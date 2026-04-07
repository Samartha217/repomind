def build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into context for LLM."""

    if not chunks:
        return "No relevant code found."

    context_parts = []

    for i, chunk in enumerate(chunks, 1):
        # Extract just the code content (remove the metadata prefix we added during embedding)
        content = chunk["content"]

        # If content has our embedding prefix, extract just the code
        if "\n\n" in content:
            parts = content.split("\n\n", 1)
            if len(parts) > 1:
                content = parts[1]

        content_truncated = content.strip()

        context_parts.append(f"""
---
**Source {i}:** `{chunk['file_path']}` (lines {chunk['start_line']}-{chunk['end_line']})
**Type:** {chunk['type']} | **Name:** {chunk['name']}
```
{content_truncated}
```
""")

    return "\n".join(context_parts)


def build_sources_list(chunks: list[dict]) -> list[dict]:
    """Extract clean source references."""

    sources = []
    seen = set()

    for chunk in chunks:
        key = f"{chunk['file_path']}:{chunk['start_line']}"
        if key not in seen:
            seen.add(key)
            sources.append({
                "file": chunk["file_path"],
                "name": chunk["name"],
                "type": chunk["type"],
                "lines": f"{chunk['start_line']}-{chunk['end_line']}"
            })

    return sources
