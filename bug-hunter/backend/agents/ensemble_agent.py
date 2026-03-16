"""LLM Ensemble Agent — validates bugs using multiple LLM providers."""
import json
import asyncio
from typing import Optional

import httpx

from config import settings

SYSTEM_PROMPT = """You are an expert debugging assistant.
Analyze the code structure and detected issues.
Confirm if each bug is real.

Return a JSON array of confirmed bugs. Each bug should have:
- bug_type: string
- line_number: integer
- explanation: string
- impact: string
- suggested_fix: string
- confidence: float (0-1)

Only return the JSON array, no other text. If no bugs are real, return an empty array []."""


async def validate_with_ensemble(
    code: str,
    candidate_bugs: list[dict],
    language: str,
) -> list[dict]:
    """Send code and candidate bugs to multiple LLMs, then vote."""
    if not settings.has_any_llm:
        # No LLM keys — return candidates as-is with a note
        for bug in candidate_bugs:
            bug["llm_validated"] = False
            bug["validation_note"] = "LLM validation skipped — no API keys configured"
        return candidate_bugs

    user_prompt = _build_prompt(code, candidate_bugs, language)

    # Run all available LLMs concurrently
    tasks = []
    if settings.has_openrouter:
        tasks.append(("openrouter", _call_openrouter(user_prompt)))
    if settings.has_gemini:
        tasks.append(("gemini", _call_gemini(user_prompt)))
    if settings.has_groq:
        tasks.append(("groq", _call_groq(user_prompt)))

    responses = {}
    results = await asyncio.gather(
        *[task[1] for task in tasks],
        return_exceptions=True,
    )

    for (name, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            responses[name] = []
        else:
            responses[name] = result

    # Ensemble voting
    return _ensemble_vote(candidate_bugs, responses)


def _build_prompt(code: str, bugs: list[dict], language: str) -> str:
    """Build the prompt for LLM validation."""
    bugs_text = "\n".join(
        f"- Line {b.get('line_number', '?')}: {b.get('bug_type', 'Unknown')} — {b.get('explanation', '')}"
        for b in bugs
    )

    return f"""Language: {language}

Code:
```
{code[:3000]}
```

Candidate bugs detected by static analysis:
{bugs_text}

Analyze each bug and confirm if it is real. Return your response as a JSON array."""


async def _call_openrouter(prompt: str) -> list[dict]:
    """Call OpenRouter API."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            settings.OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "meta-llama/llama-3.1-8b-instruct:free",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 2000,
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return _parse_llm_response(content)


async def _call_gemini(prompt: str) -> list[dict]:
    """Call Google Gemini API."""
    url = f"{settings.GEMINI_URL}?key={settings.GEMINI_API_KEY}"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [
                        {"text": SYSTEM_PROMPT + "\n\n" + prompt}
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 2000,
                },
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_llm_response(content)


async def _call_groq(prompt: str) -> list[dict]:
    """Call Groq API."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            settings.GROQ_URL,
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 2000,
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return _parse_llm_response(content)


def _parse_llm_response(content: str) -> list[dict]:
    """Parse LLM response to extract bug JSON."""
    content = content.strip()

    # Try to extract JSON from markdown code blocks
    if "```" in content:
        import re
        json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1).strip()

    try:
        result = json.loads(content)
        if isinstance(result, list):
            return result
        return []
    except json.JSONDecodeError:
        return []


def _ensemble_vote(
    candidate_bugs: list[dict],
    llm_responses: dict[str, list[dict]],
) -> list[dict]:
    """Vote across LLM responses. Confirm bugs agreed by 2+ models."""
    if not llm_responses:
        return candidate_bugs

    validated_bugs = []
    total_models = len(llm_responses)

    for bug in candidate_bugs:
        line = bug.get("line_number", 0)
        votes = 0
        explanations = []
        fixes = []

        for model_name, model_bugs in llm_responses.items():
            for mb in model_bugs:
                if mb.get("line_number") == line or _bugs_match(bug, mb):
                    votes += 1
                    if mb.get("explanation"):
                        explanations.append(mb["explanation"])
                    if mb.get("suggested_fix"):
                        fixes.append(mb["suggested_fix"])
                    break

        # 2+ votes OR all models confirmed (even if only 1)
        threshold = min(2, total_models)
        if votes >= threshold:
            bug["llm_validated"] = True
            bug["validation_votes"] = f"{votes}/{total_models}"
            if explanations:
                bug["explanation"] = explanations[0]  # Use first LLM's explanation
            if fixes:
                bug["suggested_fix"] = fixes[0]
        else:
            bug["llm_validated"] = votes > 0
            bug["validation_votes"] = f"{votes}/{total_models}"

        validated_bugs.append(bug)

    return validated_bugs


def _bugs_match(bug1: dict, bug2: dict) -> bool:
    """Check if two bug reports refer to the same issue."""
    t1 = bug1.get("bug_type", "").lower()
    t2 = bug2.get("bug_type", "").lower()
    return t1 == t2 or t1 in t2 or t2 in t1
