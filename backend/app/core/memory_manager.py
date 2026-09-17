import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embedding_client import EmbeddingClient
from app.models.memory import Memory
from app.config import get_settings

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages semantic memory for ARIA using RAG pattern.
    
    Responsibilities:
    - Store new memories with their embeddings
    - Retrieve relevant memories for a given query using vector similarity
    - Handle explicit user commands ("remember that...", "forget that...")
    - Track memory access patterns for importance scoring
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_client = EmbeddingClient()
        self.settings = get_settings()
    
    async def store_memory(
        self,
        user_id: uuid.UUID,
        content: str,
        category: str = "other",
        source: str = "extracted",
        importance: float = 0.5,
    ) -> Memory:
        """Store a new memory with its embedding vector."""
        # 1. Generate embedding for the content
        embedding = await self.embedding_client.embed(content)
        
        # 2. Check for duplicate/very similar memories (cosine similarity > 0.92)
        #    If found, update the existing memory instead of creating a new one
        existing = await self._find_duplicate(user_id, embedding, threshold=0.92)
        if existing:
            logger.info(f"Updating existing memory (similarity > 0.92): {existing.id}")
            existing.content = content
            existing.embedding = embedding
            existing.updated_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        
        # 3. Create new memory
        memory = Memory(
            user_id=user_id,
            content=content,
            category=category,
            source=source,
            importance=importance,
            embedding=embedding,
        )
        self.db.add(memory)
        await self.db.commit()
        await self.db.refresh(memory)
        logger.info(f"Stored new memory: {memory.id} [{category}] {content[:50]}...")
        return memory
    
    async def retrieve_relevant(
        self,
        user_id: uuid.UUID,
        query: str,
        top_k: int | None = None,
        min_similarity: float | None = None,
    ) -> list[Memory]:
        """Retrieve the most relevant memories for a query using vector similarity.
        
        This is the core RAG retrieval: 
        1. Embed the query
        2. Find nearest neighbors in the memory vectors
        3. Update access counts
        4. Return sorted by relevance
        """
        top_k = top_k or self.settings.memory_top_k
        min_similarity = min_similarity or self.settings.memory_similarity_threshold
        
        # Generate query embedding
        query_embedding = await self.embedding_client.embed(query)
        
        # Use pgvector's cosine distance operator (<=>) to find nearest memories
        # Cosine distance = 1 - cosine_similarity, so lower is more similar
        # We use raw SQL for the vector operation since SQLAlchemy ORM support for pgvector 
        # distance operators can be tricky
        query_embedding_str = str(query_embedding)
        
        result = await self.db.execute(
            text("""
                SELECT id, content, category, source, importance, access_count,
                       created_at, updated_at,
                       1 - (embedding <=> :query_embedding::vector) as similarity
                FROM memories
                WHERE user_id = :user_id 
                  AND is_active = true
                  AND 1 - (embedding <=> :query_embedding::vector) >= :min_similarity
                ORDER BY embedding <=> :query_embedding::vector
                LIMIT :top_k
            """),
            {
                "query_embedding": query_embedding_str,
                "user_id": str(user_id),
                "min_similarity": min_similarity,
                "top_k": top_k,
            },
        )
        rows = result.fetchall()
        
        if not rows:
            return []
        
        # Update access counts for retrieved memories
        memory_ids = [row.id for row in rows]
        await self.db.execute(
            update(Memory)
            .where(Memory.id.in_(memory_ids))
            .values(
                access_count=Memory.access_count + 1,
                last_accessed_at=datetime.now(timezone.utc),
            )
        )
        await self.db.commit()
        
        # Convert rows to Memory objects for the caller
        memories = []
        for row in rows:
            mem = await self.db.get(Memory, row.id)
            if mem:
                memories.append(mem)
        
        logger.info(f"Retrieved {len(memories)} relevant memories for query: {query[:50]}...")
        return memories
    
    async def format_memories_as_context(self, memories: list[Memory]) -> str:
        """Format retrieved memories into a context string for the LLM prompt."""
        if not memories:
            return ""
        
        lines = ["Here is what you remember about the user (use this context to personalize your response):"]
        for i, mem in enumerate(memories, 1):
            lines.append(f"  {i}. [{mem.category}] {mem.content}")
        return "\n".join(lines)
    
    async def add_explicit_memory(
        self,
        user_id: uuid.UUID,
        content: str,
        category: str = "other",
    ) -> Memory:
        """Add a memory explicitly requested by the user ('remember that...')."""
        return await self.store_memory(
            user_id=user_id,
            content=content,
            category=category,
            source="explicit",
            importance=0.8,  # Explicit memories get higher importance
        )
    
    async def forget_memory(
        self,
        user_id: uuid.UUID,
        memory_id: uuid.UUID,
    ) -> bool:
        """Soft-delete a memory (set is_active=False)."""
        result = await self.db.execute(
            update(Memory)
            .where(Memory.id == memory_id, Memory.user_id == user_id)
            .values(is_active=False)
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def forget_by_content(
        self,
        user_id: uuid.UUID,
        content_query: str,
    ) -> int:
        """Forget memories similar to the given content query."""
        # Find similar memories
        query_embedding = await self.embedding_client.embed(content_query)
        query_embedding_str = str(query_embedding)
        
        result = await self.db.execute(
            text("""
                UPDATE memories 
                SET is_active = false
                WHERE user_id = :user_id 
                  AND is_active = true
                  AND 1 - (embedding <=> :query_embedding::vector) >= 0.8
            """),
            {
                "query_embedding": query_embedding_str,
                "user_id": str(user_id),
            },
        )
        await self.db.commit()
        count = result.rowcount
        logger.info(f"Forgot {count} memories matching: {content_query[:50]}...")
        return count
    
    async def list_memories(
        self,
        user_id: uuid.UUID,
        category: str | None = None,
        source: str | None = None,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Memory], int]:
        """List memories with optional filtering. Returns (memories, total_count)."""
        query = select(Memory).where(Memory.user_id == user_id)
        count_query = select(text("count(*)")).select_from(Memory).where(Memory.user_id == user_id)
        
        if active_only:
            query = query.where(Memory.is_active == True)
            count_query = count_query.where(Memory.is_active == True)
        if category:
            query = query.where(Memory.category == category)
            count_query = count_query.where(Memory.category == category)
        if source:
            query = query.where(Memory.source == source)
            count_query = count_query.where(Memory.source == source)
        
        query = query.order_by(Memory.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        memories = list(result.scalars().all())
        
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        return memories, total
    
    async def _find_duplicate(
        self,
        user_id: uuid.UUID,
        embedding: list[float],
        threshold: float = 0.92,
    ) -> Memory | None:
        """Find an existing memory that is very similar to the given embedding."""
        embedding_str = str(embedding)
        result = await self.db.execute(
            text("""
                SELECT id
                FROM memories
                WHERE user_id = :user_id 
                  AND is_active = true
                  AND 1 - (embedding <=> :embedding::vector) >= :threshold
                ORDER BY embedding <=> :embedding::vector
                LIMIT 1
            """),
            {
                "embedding": embedding_str,
                "user_id": str(user_id),
                "threshold": threshold,
            },
        )
        row = result.fetchone()
        if row:
            return await self.db.get(Memory, row.id)
        return None
