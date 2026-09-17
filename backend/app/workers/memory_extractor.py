import logging
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# This task runs after each conversation to extract facts/preferences
@celery_app.task(name="extract_memories")
def extract_memories(user_id: str, conversation_messages: list[dict]):
    """Extract facts and preferences from a conversation and store as memories.
    
    This runs asynchronously after each conversation completes.
    It uses the LLM to analyze the conversation and identify:
    - Personal facts (name, location, job, etc.)
    - Preferences (favorite things, interests)
    - Routine information (work schedule, commute)
    - Important events or dates
    
    Each extracted fact is stored as an individual memory with its embedding.
    """
    import asyncio
    asyncio.run(_extract_memories_async(user_id, conversation_messages))


async def _extract_memories_async(user_id: str, conversation_messages: list[dict]):
    """Async implementation of memory extraction."""
    from uuid import UUID
    from app.core.llm_client import LLMClient
    from app.core.memory_manager import MemoryManager  
    from app.db.session import async_session_factory
    
    llm = LLMClient()
    
    # Build the conversation text
    conversation_text = "\n".join(
        f"{msg['role']}: {msg['content']}" 
        for msg in conversation_messages 
        if msg.get('content') and msg['role'] in ('user', 'assistant')
    )
    
    if len(conversation_text) < 20:  # Too short to extract anything
        return
    
    # Ask the LLM to extract facts (use a cheap/fast call without tools)
    extraction_prompt = [
        {
            "role": "system",
            "content": (
                "You are a memory extraction assistant. Analyze the following conversation "
                "and extract concrete, specific facts about the user. "
                "Return ONLY a JSON array of objects, each with 'fact' (string) and 'category' "
                "(one of: personal, preference, location, work, finance, health, other). "
                "Only extract NEW information - things the user explicitly stated or clearly implied. "
                "Do NOT extract opinions, questions, or transient information. "
                "If there are no new facts to extract, return an empty array []. "
                "Examples of good facts: "
                '  {"fact": "Lives in Valencia, Spain", "category": "location"} '
                '  {"fact": "Works at Company X as a software engineer", "category": "work"} '
                '  {"fact": "Interested in cryptocurrency and AI", "category": "preference"} '
            )
        },
        {
            "role": "user",
            "content": f"Extract facts from this conversation:\n\n{conversation_text}"
        }
    ]
    
    try:
        completion = await llm.chat(extraction_prompt, temperature=0.1)
        response_text = completion.choices[0].message.content
        
        # Parse the JSON response
        import json
        # Try to find JSON array in the response (model might wrap it in markdown)
        import re
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if not json_match:
            logger.info("No facts extracted from conversation")
            return
        
        facts = json.loads(json_match.group())
        
        if not facts:
            logger.info("No facts extracted from conversation")
            return
        
        # Store each fact as a memory
        async with async_session_factory() as db:
            memory_manager = MemoryManager(db)
            for fact_data in facts:
                fact = fact_data.get("fact", "").strip()
                category = fact_data.get("category", "other").strip()
                if fact and len(fact) > 5:
                    await memory_manager.store_memory(
                        user_id=UUID(user_id),
                        content=fact,
                        category=category,
                        source="extracted",
                    )
            logger.info(f"Extracted and stored {len(facts)} memories from conversation")
    
    except Exception as e:
        logger.error(f"Failed to extract memories: {e}")
