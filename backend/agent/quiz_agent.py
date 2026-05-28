"""
ADK-powered quiz generation agent.

Architecture — hybrid "pre-retrieve then generate" pattern:
  1. Retrieve context for QUESTIONS_PER_QUIZ topics from ChromaDB (no LLM).
  2. Pass the aggregated context to the ADK Agent in a single prompt.
  3. Agent makes ONE LLM call to generate all MCQs as structured JSON.

Keeps the full ADK pipeline (system prompt, guardrails, lifecycle) while
staying within free-tier rate limits (no multi-turn tool-calling loop).
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import re
import sys
import time
from collections.abc import Callable

# Python 3.9 + Windows: ProactorEventLoop raises SSL errors on cleanup.
# SelectorEventLoop handles it cleanly.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from backend.config import GEMINI_MODEL, QUESTIONS_PER_QUIZ
from backend.rag.retriever import search_knowledge_base

# ── Topic pool — first QUESTIONS_PER_QUIZ entries are used each run ────────

_ALL_TOPICS = [
    "gas turbine thermodynamic Brayton cycle stages",
    "axial flow compressor design stages pressure ratio",
    "centrifugal compressor impeller diffuser operation",
    "combustion chamber annular can cannular design",
    "turbine blade cooling film convection techniques",
    "turbofan bypass ratio high low classification thrust",
    "compressor stall surge causes prevention rotating stall",
    "engine performance parameters EPR EGT N1 N2 FADEC",
    "specific fuel consumption thrust propulsive efficiency",
    "turboprop turboshaft power extraction gearbox propeller",
]

_RETRIEVAL_TOPICS = _ALL_TOPICS[:QUESTIONS_PER_QUIZ]

# ── System prompt (guardrails) ─────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an expert EASA Part-66 propulsion exam preparation assistant for \
aerospace and aeronautical engineering students (ages 22–30).

━━ GROUNDING RULES (non-negotiable) ━━
• Base every question, every distractor, and every explanation EXCLUSIVELY \
on the EASA reference passages provided in the user message.
• Do NOT invent, extrapolate, or assume technical facts beyond the given text.
• If a passage is too short for a standalone question, combine it with a \
related passage rather than fabricating content.

━━ QUESTION QUALITY STANDARDS ━━
• Generate exactly ONE question per topic block in the provided context.
• Exactly 4 options per question (A, B, C, D).
• Exactly ONE unambiguously correct answer per question.
• Distractors must be plausible but clearly wrong to a knowledgeable student.
• Use precise aerospace terminology: bypass ratio, compressor stall/surge, \
turbine inlet temperature, EPR, EGT, FADEC, BPR, SFC, OPR, Brayton cycle.
• Academic tone — engaging yet technically rigorous.
• Zero profanity, informal language, or inappropriate content.

━━ OUTPUT FORMAT ━━
Return ONLY valid JSON — no preamble, no markdown fences, no trailing text:
{
  "questions": [
    {
      "id": 1,
      "question": "Precise technical question?",
      "options": {"A": "…", "B": "…", "C": "…", "D": "…"},
      "correct_answer": "A",
      "explanation": "Detailed explanation citing EASA concepts."
    }
  ]
}
"""


def _build_context_prompt() -> str:
    """
    Pre-fetch context for all topics and embed it directly in the prompt.

    This eliminates the multi-turn tool-calling loop (and its ~20 LLM calls)
    in favour of a single, context-rich generation request.
    """
    sections: list[str] = []
    for i, topic in enumerate(_RETRIEVAL_TOPICS, start=1):
        context = search_knowledge_base(topic)
        sections.append(
            f"### Topic {i}: {topic}\n\n{context}"
        )

    context_block = "\n\n---\n\n".join(sections)

    n = len(_RETRIEVAL_TOPICS)
    header = (
        f"Below are {n} topic blocks retrieved from the official EASA "
        "propulsion documentation. Generate exactly ONE rigorous "
        "multiple-choice question per topic block, grounded exclusively "
        "in the provided text.\n\n"
    )
    footer = (
        f"\n\nNow produce the {n}-question JSON as specified in your "
        "instructions."
    )
    return header + context_block + footer


# ── Async agent execution ──────────────────────────────────────────────────

async def _run_agent(prompt: str) -> str:
    """Run the ADK agent with a pre-built context prompt; returns raw text."""
    session_service = InMemorySessionService()
    agent = Agent(
        name="easa_quiz_agent",
        model=GEMINI_MODEL,
        instruction=_SYSTEM_PROMPT,
    )
    runner = Runner(
        agent=agent,
        app_name="quiz_propulsao",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="quiz_propulsao",
        user_id="student",
    )

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)],
    )

    raw = ""
    async for event in runner.run_async(
        user_id="student",
        session_id=session.id,
        new_message=message,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    raw += part.text

    return raw


# ── JSON parsing ───────────────────────────────────────────────────────────

def _parse_response(raw: str) -> dict:
    """Extract and validate the JSON quiz payload from the agent's response."""
    clean = re.sub(r"```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    clean = re.sub(r"```", "", clean).strip()

    start = clean.find("{")
    end = clean.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(
            f"No JSON object in agent response. Snippet: {raw[:300]!r}"
        )

    data = json.loads(clean[start:end])

    if not data.get("questions"):
        raise ValueError("Agent returned JSON with an empty 'questions' list.")

    return data


# ── Retry config ───────────────────────────────────────────────────────────

_MAX_RETRIES = 3
_RETRY_WAIT_SECONDS = [30, 60]  # wait before attempt 2, then attempt 3


def _is_retryable(exc: Exception) -> bool:
    """503 UNAVAILABLE is a transient server overload — safe to retry."""
    return "503" in str(exc) or "UNAVAILABLE" in str(exc)


# ── Public synchronous interface ───────────────────────────────────────────

def generate_quiz(
    on_retry: Callable[[int, int, int], None] | None = None,
) -> dict:
    """
    Generate a QUESTIONS_PER_QUIZ-question EASA propulsion quiz.

    Retries up to _MAX_RETRIES times on transient 503 UNAVAILABLE errors,
    with progressive waits between attempts.

    Args:
        on_retry: Optional callback invoked before each retry with
                  (attempt, max_retries, wait_seconds) so the caller
                  can update a status UI.

    Returns:
        dict: {"questions": [...]} — each item has id, question, options,
              correct_answer, and explanation.

    Raises:
        RuntimeError: On persistent failure or malformed JSON response.
        TimeoutError: If a single attempt exceeds 180 seconds.
    """
    prompt = _build_context_prompt()

    def _thread_worker() -> str:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_run_agent(prompt))
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            loop.close()

    last_exc: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_thread_worker)
                try:
                    raw = future.result(timeout=180)
                except concurrent.futures.TimeoutError as exc:
                    raise TimeoutError(
                        "Quiz generation timed out after 180 seconds."
                    ) from exc
            return _parse_response(raw)

        except TimeoutError:
            raise
        except Exception as exc:
            last_exc = exc
            if _is_retryable(exc) and attempt < _MAX_RETRIES:
                wait = _RETRY_WAIT_SECONDS[attempt - 1]
                if on_retry:
                    on_retry(attempt, _MAX_RETRIES, wait)
                time.sleep(wait)
            else:
                raise

    raise RuntimeError(
        f"Quiz generation failed after {_MAX_RETRIES} attempts: {last_exc}"
    )
