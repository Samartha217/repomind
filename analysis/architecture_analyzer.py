"""
Architecture Analyzer — deterministic pipeline replacing LLM-guessed structure.

Pipeline:
1. Build a real NetworkX import graph from AST/Tree-sitter data
2. Louvain community detection groups tightly-connected files into layers
3. External services detected from import names (lookup table)
4. LLM writes 1-sentence descriptions per layer (only remaining LLM call)
5. Mermaid diagram generated from real data — zero hallucinations
"""

import json
from pathlib import Path

import networkx as nx
from community import best_partition
from langchain_google_genai import ChatGoogleGenerativeAI

from config import GOOGLE_API_KEY, LLM_MODEL

# ── External service detection ─────────────────────────────────────────────────

EXTERNAL_SERVICE_MAP = {
    "chromadb": {"name": "ChromaDB", "type": "database"},
    "langchain_google_genai": {"name": "Google Gemini", "type": "ai"},
    "langchain_groq": {"name": "Groq", "type": "ai"},
    "langchain_ollama": {"name": "Ollama (Embeddings)", "type": "ai"},
    "langchain_openai": {"name": "OpenAI API", "type": "ai"},
    "openai": {"name": "OpenAI API", "type": "ai"},
    "anthropic": {"name": "Anthropic API", "type": "ai"},
    "requests": {"name": "HTTP API", "type": "external_api"},
    "httpx": {"name": "HTTP API", "type": "external_api"},
    "aiohttp": {"name": "HTTP API", "type": "external_api"},
    "gitpython": {"name": "GitHub", "type": "external_api"},
    "git": {"name": "GitHub", "type": "external_api"},
    "psycopg2": {"name": "PostgreSQL", "type": "database"},
    "psycopg": {"name": "PostgreSQL", "type": "database"},
    "pymysql": {"name": "MySQL", "type": "database"},
    "pymongo": {"name": "MongoDB", "type": "database"},
    "motor": {"name": "MongoDB", "type": "database"},
    "redis": {"name": "Redis", "type": "database"},
    "aioredis": {"name": "Redis", "type": "database"},
    "sqlalchemy": {"name": "SQLAlchemy", "type": "database"},
    "boto3": {"name": "AWS S3", "type": "storage"},
    "botocore": {"name": "AWS", "type": "storage"},
    "google.cloud": {"name": "Google Cloud", "type": "storage"},
    "azure": {"name": "Azure", "type": "storage"},
    "flask": {"name": "Flask", "type": "api"},
    "fastapi": {"name": "FastAPI", "type": "api"},
    "django": {"name": "Django", "type": "api"},
    "starlette": {"name": "Starlette", "type": "api"},
    "celery": {"name": "Celery", "type": "external_api"},
    "kafka": {"name": "Kafka", "type": "external_api"},
    "pika": {"name": "RabbitMQ", "type": "external_api"},
    "stripe": {"name": "Stripe API", "type": "external_api"},
    "twilio": {"name": "Twilio API", "type": "external_api"},
    "sendgrid": {"name": "SendGrid", "type": "external_api"},
    "elasticsearch": {"name": "Elasticsearch", "type": "database"},
    "pinecone": {"name": "Pinecone", "type": "database"},
    "weaviate": {"name": "Weaviate", "type": "database"},
    "qdrant": {"name": "Qdrant", "type": "database"},
}

# Layer color palette (used by both Mermaid and Pyvis)
LAYER_COLORS = [
    "#667eea",  # indigo
    "#10b981",  # emerald
    "#f59e0b",  # amber
    "#ec4899",  # pink
    "#06b6d4",  # cyan
    "#f97316",  # orange
    "#8b5cf6",  # violet
    "#14b8a6",  # teal
]


# ── Graph building ─────────────────────────────────────────────────────────────

def build_graph(files_analysis: dict) -> nx.DiGraph:
    """Build a directed NetworkX graph from the real import data."""

    G = nx.DiGraph()

    # Add all files as nodes
    for file_path, info in files_analysis["files"].items():
        G.add_node(file_path, **{
            "is_entry_point": info.get("is_entry_point", False),
            "classes": [c["name"] for c in info.get("classes", [])],
            "functions": [f["name"] for f in info.get("functions", [])],
            "language": info.get("language", ".py"),
        })

    # Add real import edges
    file_stems = {Path(f).stem: f for f in files_analysis["files"]}

    for dep in files_analysis.get("dependencies", []):
        src = dep["from"]
        module = dep["to"]
        module_base = module.split(".")[0]

        # Resolve module name to actual file path
        target = file_stems.get(module_base)
        if target and target != src and G.has_node(target):
            if not G.has_edge(src, target):
                G.add_edge(src, target)

    return G


def detect_clusters(G: nx.DiGraph, files_analysis: dict) -> dict:
    """
    Group files into clusters using Louvain community detection.
    Falls back to directory-based grouping if graph has no edges.
    Returns: {file_path: cluster_id}
    """
    if G.number_of_edges() == 0:
        # Fallback: group by top-level directory
        cluster_map = {}
        dir_ids = {}
        for file_path in G.nodes():
            top_dir = Path(file_path).parts[0] if len(Path(file_path).parts) > 1 else "root"
            if top_dir not in dir_ids:
                dir_ids[top_dir] = len(dir_ids)
            cluster_map[file_path] = dir_ids[top_dir]
        return cluster_map

    try:
        G_undirected = G.to_undirected()
        partition = best_partition(G_undirected)
        return partition
    except Exception:
        # Final fallback: all files in one cluster
        return {f: 0 for f in G.nodes()}


def detect_external_services(files_analysis: dict) -> list[dict]:
    """Detect external services by scanning all imports against the lookup table."""

    found = {}
    for file_info in files_analysis["files"].values():
        for imp in file_info.get("imports", []):
            module = (imp.get("from_module") or imp.get("module") or "").split(".")[0].lower()
            if module in EXTERNAL_SERVICE_MAP and module not in found:
                found[module] = EXTERNAL_SERVICE_MAP[module]

    return list(found.values())


# ── Cluster naming (LLM) ───────────────────────────────────────────────────────

def _name_clusters_with_llm(cluster_contents: dict) -> dict:
    """
    Ask LLM to name each cluster with a short layer name + 1-sentence description.
    cluster_contents: {cluster_id: [file_path, ...]}
    Returns: {cluster_id: {"name": str, "description": str}}
    """
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0,
    )

    lines = []
    for cid, files in sorted(cluster_contents.items()):
        lines.append(f"Cluster {cid}: {', '.join(files)}")

    prompt = f"""You are analyzing a software project's architecture.
Below are groups of files that are tightly connected via imports.
For each cluster, give a short layer name (2-4 words) and one sentence describing what it does.

{chr(10).join(lines)}

Return ONLY a JSON object like this:
{{
  "0": {{"name": "Ingestion Layer", "description": "Handles cloning, parsing, and embedding repositories."}},
  "1": {{"name": "Retrieval Layer", "description": "Searches the vector store and builds context for the LLM."}}
}}

Use only the cluster numbers shown above. Return ONLY valid JSON."""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return json.loads(content.strip())
    except Exception:
        # Fallback: generic names
        return {str(cid): {"name": f"Layer {cid}", "description": ""} for cid in cluster_contents}


# ── Main analyzer ──────────────────────────────────────────────────────────────

class ArchitectureAnalyzer:
    def analyze(self, files_analysis: dict) -> dict:
        """
        Build accurate architecture from real import graph.
        Returns same schema as before so app.py needs no changes.
        """
        # Step 1: Real import graph
        G = build_graph(files_analysis)

        # Step 2: Community detection → layer groupings
        cluster_map = detect_clusters(G, files_analysis)

        # Step 3: External services from import names
        external_services = detect_external_services(files_analysis)

        # Step 4: Group files by cluster
        cluster_contents: dict[int, list] = {}
        for file_path, cid in cluster_map.items():
            cluster_contents.setdefault(cid, []).append(file_path)

        # Step 5: LLM names each cluster (1 call, not 1-per-file)
        cluster_names = _name_clusters_with_llm(cluster_contents)

        # Step 6: Build layers list (same schema as before)
        layers = []
        for cid, files in sorted(cluster_contents.items()):
            meta = cluster_names.get(str(cid), {"name": f"Layer {cid}", "description": ""})
            components = []
            for file_path in files:
                info = files_analysis["files"].get(file_path, {})
                comp_type = _infer_component_type(file_path, info)
                components.append({
                    "file": file_path,
                    "name": Path(file_path).stem,
                    "type": comp_type,
                    "description": meta.get("description", ""),
                })
            layers.append({
                "name": meta["name"],
                "description": meta.get("description", ""),
                "components": components,
            })

        # Step 7: Build connections from real edges (not LLM-guessed)
        connections = []
        seen = set()
        for src, dst in G.edges():
            src_name = Path(src).stem
            dst_name = Path(dst).stem
            key = f"{src_name}->{dst_name}"
            if key not in seen:
                seen.add(key)
                connections.append({
                    "from": src_name,
                    "to": dst_name,
                    "label": "imports",
                })

        return {
            "layers": layers,
            "connections": connections,
            "external_services": external_services,
            "_graph": G,              # passed to Pyvis — not rendered by Mermaid
            "_cluster_map": cluster_map,
        }


def _infer_component_type(file_path: str, info: dict) -> str:
    """Infer component type from file path and content."""
    path = file_path.lower()
    if any(x in path for x in ["app.", "main.", "index.", "run.", "cli."]):
        return "api"
    if any(x in path for x in ["config", "setting", "env"]):
        return "config"
    if any(x in path for x in ["test_", "_test", "spec"]):
        return "utils"
    if any(x in path for x in ["model", "schema", "entity"]):
        return "model"
    if any(x in path for x in ["db", "database", "storage", "embed", "vector"]):
        return "database"
    if any(x in path for x in ["route", "endpoint", "view", "controller", "handler"]):
        return "api"
    if any(x in path for x in ["service", "manager", "orchestrat"]):
        return "service"
    if any(x in path for x in ["util", "helper", "tool", "common"]):
        return "utils"
    return "service"


def generate_professional_diagram(architecture: dict) -> str:
    """Generate a Mermaid diagram from the architecture dict."""

    lines = ["flowchart TB"]

    if architecture.get("external_services"):
        lines.append('    subgraph external["☁️ External Services"]')
        lines.append("        direction LR")
        for svc in architecture["external_services"]:
            svc_id = _to_id(svc["name"])
            icon = _get_icon(svc["type"])
            lines.append(f'        {svc_id}[["{icon} {_safe_label(svc["name"])}"]]')
        lines.append("    end")
        lines.append("")

    for layer in architecture.get("layers", []):
        layer_id = _to_id(layer["name"])
        lines.append(f'    subgraph {layer_id}["{_safe_label(layer["name"])}"]')
        lines.append("        direction LR")
        for comp in layer.get("components", []):
            comp_id = _to_id(comp["name"])
            icon = _get_icon(comp["type"])
            lines.append(f'        {comp_id}["{icon} {_safe_label(comp["name"])}"]')
        lines.append("    end")
        lines.append("")

    for conn in architecture.get("connections", []):
        from_id = _to_id(conn["from"])
        to_id = _to_id(conn["to"])
        label = conn.get("label", "")
        if label:
            lines.append(f'    {from_id} -->|"{label}"| {to_id}')
        else:
            lines.append(f"    {from_id} --> {to_id}")

    lines += [
        "",
        "    classDef api fill:#3b82f6,stroke:#2563eb,color:#fff",
        "    classDef service fill:#8b5cf6,stroke:#7c3aed,color:#fff",
        "    classDef database fill:#10b981,stroke:#059669,color:#fff",
        "    classDef config fill:#f59e0b,stroke:#d97706,color:#fff",
        "    classDef external fill:#ec4899,stroke:#db2777,color:#fff",
        "    classDef model fill:#06b6d4,stroke:#0891b2,color:#fff",
        "    classDef utils fill:#64748b,stroke:#475569,color:#fff",
    ]

    for layer in architecture.get("layers", []):
        for comp in layer.get("components", []):
            comp_id = _to_id(comp["name"])
            comp_type = comp.get("type", "service")
            if comp_type in ("api", "service", "database", "config", "model", "utils"):
                lines.append(f"    class {comp_id} {comp_type}")

    for svc in architecture.get("external_services", []):
        svc_id = _to_id(svc["name"])
        lines.append(f"    class {svc_id} external")

    return "\n".join(lines)


def _to_id(name: str) -> str:
    import re
    result = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
    result = re.sub(r"_+", "_", result).strip("_")
    if result and result[0].isdigit():
        result = "n_" + result
    return result or "node"


def _safe_label(name: str) -> str:
    """Strip characters that would break a Mermaid quoted label."""
    return name.replace('"', "'").replace("[", "(").replace("]", ")")


def _get_icon(component_type: str) -> str:
    return {
        "api": "🌐", "service": "⚙️", "database": "🗄️",
        "config": "📝", "utils": "🔧", "model": "📊",
        "agent": "🤖", "external": "☁️", "external_api": "☁️",
        "ai": "🧠", "storage": "💾", "email": "📧",
    }.get(component_type, "📦")
