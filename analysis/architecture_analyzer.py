import json

from langchain_openai import ChatOpenAI

from config import LLM_MODEL, OPENAI_API_KEY


class ArchitectureAnalyzer:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=OPENAI_API_KEY,
            temperature=0
        )

    def analyze(self, files_analysis: dict) -> dict:
        """Deep analysis of codebase architecture using LLM."""

        # Build a summary of the codebase
        codebase_summary = self._build_codebase_summary(files_analysis)

        # Use LLM to analyze architecture
        architecture = self._analyze_with_llm(codebase_summary)

        return architecture

    def _build_codebase_summary(self, files_analysis: dict) -> str:
        """Build a detailed summary of the codebase."""

        summary = "CODEBASE STRUCTURE:\n\n"

        for file_path, info in files_analysis["files"].items():
            summary += f"FILE: {file_path}\n"

            if info["is_entry_point"]:
                summary += "  [ENTRY POINT]\n"

            if info["classes"]:
                summary += "  CLASSES:\n"
                for cls in info["classes"]:
                    summary += f"    - {cls['name']}"
                    if cls["methods"]:
                        methods = [m["name"] for m in cls["methods"]]
                        summary += f" (methods: {', '.join(methods[:5])})"
                    summary += "\n"

            if info["functions"]:
                summary += "  FUNCTIONS:\n"
                for func in info["functions"]:
                    summary += f"    - {func['name']}({', '.join(func['args'][:3])})\n"

            summary += "\n"

        summary += "DEPENDENCIES:\n"
        for dep in files_analysis["dependencies"]:
            summary += f"  {dep['from']} --> {dep['to']}\n"

        return summary

    def _analyze_with_llm(self, codebase_summary: str) -> dict:
        """Use LLM to analyze and categorize the architecture."""

        prompt = f"""Analyze this codebase and provide a structured architecture breakdown.

{codebase_summary}

Return a JSON object with this EXACT structure:
{{
    "layers": [
        {{
            "name": "Layer Name (e.g., API Layer, Service Layer, Data Layer)",
            "description": "Brief description",
            "components": [
                {{
                    "file": "actual/file/path.py",
                    "name": "ComponentName",
                    "type": "api|service|database|config|utils|model|agent|scraper|external",
                    "description": "What this component does"
                }}
            ]
        }}
    ],
    "connections": [
        {{
            "from": "component_name",
            "to": "component_name",
            "label": "What flows between them (e.g., HTTP Request, DB Query, Data)"
        }}
    ],
    "external_services": [
        {{
            "name": "Service Name (e.g., OpenAI API, PostgreSQL)",
            "type": "ai|database|storage|email|external_api"
        }}
    ]
}}

Rules:
1. Group files into logical layers (typically 3-5 layers)
2. Identify the ACTUAL data flow, not just imports
3. Include external services the code interacts with
4. Keep component names short but descriptive
5. Label connections with what actually flows between them

Return ONLY valid JSON, no explanation."""

        response = self.llm.invoke(prompt)

        try:
            # Clean the response
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            return json.loads(content.strip())
        except json.JSONDecodeError:
            # Fallback structure
            return {
                "layers": [],
                "connections": [],
                "external_services": []
            }


def generate_professional_diagram(architecture: dict) -> str:
    """Generate a professional Mermaid diagram from architecture analysis."""

    lines = ["flowchart TB"]

    # Add external services at the top
    if architecture.get("external_services"):
        lines.append("    subgraph external[\"☁️ External Services\"]")
        lines.append("        direction LR")
        for svc in architecture["external_services"]:
            svc_id = _to_id(svc["name"])
            icon = _get_icon(svc["type"])
            lines.append(f"        {svc_id}[[\"{icon} {svc['name']}\"]]")
        lines.append("    end")
        lines.append("")

    # Add each layer as a subgraph
    for i, layer in enumerate(architecture.get("layers", [])):
        layer_id = _to_id(layer["name"])
        lines.append(f"    subgraph {layer_id}[\"{layer['name']}\"]")
        lines.append("        direction LR")

        for comp in layer.get("components", []):
            comp_id = _to_id(comp["name"])
            icon = _get_icon(comp["type"])
            lines.append(f"        {comp_id}[\"{icon} {comp['name']}\"]")

        lines.append("    end")
        lines.append("")

    # Add connections with labels
    for conn in architecture.get("connections", []):
        from_id = _to_id(conn["from"])
        to_id = _to_id(conn["to"])
        label = conn.get("label", "")

        if label:
            lines.append(f"    {from_id} -->|\"{label}\"| {to_id}")
        else:
            lines.append(f"    {from_id} --> {to_id}")

    # Add styles
    lines.append("")
    lines.append("    classDef api fill:#3b82f6,stroke:#2563eb,color:#fff")
    lines.append("    classDef service fill:#8b5cf6,stroke:#7c3aed,color:#fff")
    lines.append("    classDef database fill:#10b981,stroke:#059669,color:#fff")
    lines.append("    classDef config fill:#f59e0b,stroke:#d97706,color:#fff")
    lines.append("    classDef external fill:#ec4899,stroke:#db2777,color:#fff")
    lines.append("    classDef model fill:#06b6d4,stroke:#0891b2,color:#fff")
    lines.append("    classDef agent fill:#f97316,stroke:#ea580c,color:#fff")

    # Apply styles based on component types
    for layer in architecture.get("layers", []):
        for comp in layer.get("components", []):
            comp_id = _to_id(comp["name"])
            comp_type = comp.get("type", "service")
            lines.append(f"    class {comp_id} {comp_type}")

    # Style external services
    for svc in architecture.get("external_services", []):
        svc_id = _to_id(svc["name"])
        lines.append(f"    class {svc_id} external")

    return "\n".join(lines)


def _to_id(name: str) -> str:
    """Convert name to valid Mermaid ID."""
    return name.replace(" ", "_").replace("-", "_").replace(".", "_").replace("/", "_").lower()


def _get_icon(component_type: str) -> str:
    """Get icon for component type."""
    icons = {
        "api": "🌐",
        "service": "⚙️",
        "database": "🗄️",
        "config": "📝",
        "utils": "🔧",
        "model": "📊",
        "agent": "🤖",
        "scraper": "🕷️",
        "external": "☁️",
        "external_api": "☁️",
        "ai": "🧠",
        "storage": "💾",
        "email": "📧",
        "entry": "🚀"
    }
    return icons.get(component_type, "📦")
