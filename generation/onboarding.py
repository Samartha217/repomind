"""
Onboarding Mode — generates a guided walkthrough of any indexed codebase.
Helps new contributors understand: where to start, reading order,
key concepts, and how data flows through the system.
"""

import json

from langchain_google_genai import ChatGoogleGenerativeAI

from config import GOOGLE_API_KEY, LLM_MODEL

# Max chars of codebase summary to send to the LLM
MAX_SUMMARY_CHARS = 40000


def _build_codebase_summary(retriever) -> str:
    """
    Pull representative chunks from the vector store to give the LLM
    a picture of the codebase without sending everything.
    """
    queries = [
        "entry point main application",
        "configuration settings",
        "data models classes",
        "API routes endpoints",
        "database storage",
        "utility helper functions",
    ]

    seen_files = set()
    summary_parts = []

    for query in queries:
        chunks = retriever.search(query, top_k=2)
        for chunk in chunks:
            if chunk["file_path"] in seen_files:
                continue
            seen_files.add(chunk["file_path"])
            snippet = chunk["content"][:300].strip()
            summary_parts.append(
                f"FILE: {chunk['file_path']}\n"
                f"TYPE: {chunk['type']} | NAME: {chunk['name']}\n"
                f"SNIPPET:\n{snippet}\n"
            )

    summary = "\n---\n".join(summary_parts)

    # Hard cap to stay within token limits
    return summary[:MAX_SUMMARY_CHARS]


def generate_onboarding_guide(retriever) -> dict:
    """
    Main entry point. Uses the indexed codebase to generate a full
    onboarding guide with entry points, reading order, glossary, and data flow.

    Returns:
        {
            "entry_points": [{"file": str, "reason": str}],
            "reading_order": [{"step": int, "file": str, "why": str}],
            "glossary": [{"term": str, "definition": str}],
            "data_flow": str,
            "summary": str,
        }
    """
    llm = ChatGoogleGenerativeAI(model=LLM_MODEL, google_api_key=GOOGLE_API_KEY, temperature=0.2)

    codebase_summary = _build_codebase_summary(retriever)

    prompt = f"""You are a senior engineer helping a new developer understand a codebase.

Based on the code snippets below, generate a complete onboarding guide.

CODEBASE:
{codebase_summary}

Return a JSON object with EXACTLY this structure:
{{
    "summary": "2-3 sentence plain English description of what this project does",
    "entry_points": [
        {{
            "file": "path/to/file.py",
            "reason": "why a new dev should start here"
        }}
    ],
    "reading_order": [
        {{
            "step": 1,
            "file": "path/to/file.py",
            "why": "what you learn by reading this file"
        }}
    ],
    "glossary": [
        {{
            "term": "Technical term used in this codebase",
            "definition": "Plain English explanation (1-2 sentences)"
        }}
    ],
    "data_flow": "Step by step explanation of how data moves through the system. Use arrows like: Input → Step 1 → Step 2 → Output"
}}

Rules:
1. entry_points: 2-4 files max — the most important ones to read first
2. reading_order: 5-8 files in the order a new dev should read them
3. glossary: 5-8 terms that are specific to this codebase or tech stack
4. data_flow: be concrete, mention actual file/function names
5. Use only files you actually see in the code snippets above
6. Return ONLY valid JSON, no explanation outside the JSON

Return ONLY valid JSON."""

    response = llm.invoke(prompt)
    content = response.content.strip()

    # Strip markdown code fences if present
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]

    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        # Return a safe fallback so the UI doesn't crash
        return {
            "summary": "Could not parse the onboarding guide. Try re-indexing the repository.",
            "entry_points": [],
            "reading_order": [],
            "glossary": [],
            "data_flow": "",
        }
