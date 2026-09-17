import logging
import asyncio
from uuid import UUID
from datetime import datetime, timezone, timedelta
import redis
from sqlalchemy import select
from app.workers.celery_app import celery_app
from app.config import get_settings
from app.models.message import Message
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)

@celery_app.task(name="extract_memories_for_conversation")
def extract_memories_for_conversation(user_id: str, conversation_id: str):
    """Debounced task that extracts facts after a period of conversation inactivity."""
    settings = get_settings()
    # Check if a newer message arrived since this extraction was scheduled
    try:
        r = redis.from_url(settings.redis_url)
        last_queued = r.get(f"conv_extract_time:{conversation_id}")
        if last_queued:
            last_ts = float(last_queued)
            # If scheduled timestamp doesn't match the latest in redis, skip (debounced)
            now = datetime.now(timezone.utc).timestamp()
            if now - last_ts < 290:  # If less than ~5 mins have passed since the very last message
                return
    except Exception as e:
        logger.warning(f"Redis debounce check warning: {e}")

    asyncio.run(_extract_memories_from_db_async(user_id, conversation_id))


async def _extract_memories_from_db_async(user_id: str, conversation_id: str):
    """Loads recent messages of the conversation and extracts consolidated facts."""
    from app.core.llm_client import LLMClient
    from app.core.memory_manager import MemoryManager

    async with async_session_factory() as db:
        res = await db.execute(
            select(Message)
            .where(Message.conversation_id == UUID(conversation_id))
            .order_by(Message.created_at.desc())
            .limit(30)
        )
        msgs = list(reversed(res.scalars().all()))

        conversation_text = "\n".join(
            f"{m.role}: {m.content}"
            for m in msgs
            if m.content and m.role in ("user", "assistant")
        )

        if len(conversation_text) < 40:
            return

        llm = LLMClient()
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

            import json
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if not json_match:
                logger.info("No facts extracted from conversation")
                return

            facts = json.loads(json_match.group())
            if not facts:
                return

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
            logger.info(f"Extracted and stored {len(facts)} consolidated memories for conv {conversation_id}")
        except Exception as e:
            logger.error(f"Failed to extract memories: {e}")
