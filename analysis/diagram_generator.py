from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI
from pyvis.network import Network

from analysis.architecture_analyzer import LAYER_COLORS, ArchitectureAnalyzer, generate_professional_diagram
from config import GOOGLE_API_KEY, LLM_MODEL


def generate_mermaid_flowchart(analysis: dict) -> str:
    """Generate simplified Mermaid flowchart showing key files only."""

    lines = ["flowchart TD"]

    # Find important files: entry points + files with dependencies
    important_files = set()

    # Add entry points
    for file_path, info in analysis["files"].items():
        if info["is_entry_point"]:
            important_files.add(file_path)

    # Add files involved in dependencies
    for dep in analysis["dependencies"]:
        important_files.add(dep["from"])
        # Find the target file
        to_module = dep["to"].replace(".", "/")
        for file_path in analysis["files"].keys():
            if to_module in file_path or dep["to"] in file_path:
                important_files.add(file_path)
                break

    # Limit to max 15 files for readability
    important_files = list(important_files)[:15]

    added_nodes = set()

    # Add nodes
    for file_path in important_files:
        if file_path not in analysis["files"]:
            continue

        info = analysis["files"][file_path]
        node_id = _path_to_id(file_path)

        if node_id in added_nodes:
            continue
        added_nodes.add(node_id)

        filename = file_path.split("/")[-1]

        if info["is_entry_point"]:
            lines.append(f"    {node_id}[{filename}]:::entry")
        elif "config" in file_path.lower():
            lines.append(f"    {node_id}[{filename}]:::config")
        else:
            lines.append(f"    {node_id}[{filename}]:::module")

    # Add arrows only for important files
    added_deps = set()
    for dep in analysis["dependencies"]:
        from_id = _path_to_id(dep["from"])

        if from_id not in added_nodes:
            continue

        to_module = dep["to"].replace(".", "/")
        to_id = None

        for file_path in analysis["files"].keys():
            if to_module in file_path or dep["to"] in file_path:
                to_id = _path_to_id(file_path)
                break

        if to_id and to_id in added_nodes and from_id != to_id:
            dep_key = f"{from_id}_{to_id}"
            if dep_key not in added_deps:
                added_deps.add(dep_key)
                lines.append(f"    {from_id} --> {to_id}")

    # Add styles
    lines.append("    classDef entry fill:#10b981,stroke:#059669,color:#fff")
    lines.append("    classDef config fill:#f59e0b,stroke:#d97706,color:#fff")
    lines.append("    classDef module fill:#3b82f6,stroke:#2563eb,color:#fff")

    return "\n".join(lines)

def generate_class_diagram(analysis: dict) -> str:
    """Generate Mermaid class diagram from repo analysis."""

    lines = ["classDiagram"]

    for file_path, info in analysis["files"].items():
        for cls in info["classes"]:
            class_name = cls["name"]
            lines.append(f"    class {class_name} {{")

            for method in cls["methods"]:
                args = ", ".join(method["args"][:3])
                if len(method["args"]) > 3:
                    args += ", ..."
                lines.append(f"        +{method['name']}({args})")

            lines.append("    }")

        if info["functions"] and not info["classes"]:
            module_name = file_path.split("/")[-1].replace(".py", "").title()
            lines.append(f"    class {module_name}Utils {{")

            for func in info["functions"]:
                args = ", ".join(func["args"][:3])
                if len(func["args"]) > 3:
                    args += ", ..."
                lines.append(f"        +{func['name']}({args})")

            lines.append("    }")

    return "\n".join(lines)


def generate_architecture_description(analysis: dict) -> str:
    """Use LLM to generate human-readable architecture description."""

    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.1
    )

    context = "Repository Structure:\n\n"

    files = list(analysis["files"].items())
    entry_points = [(p, i) for p, i in files if i["is_entry_point"]]
    others = [(p, i) for p, i in files if not i["is_entry_point"]]
    selected_files = (entry_points + others)[:40]

    for file_path, info in selected_files:
        context += f"File: {file_path}"
        if info["is_entry_point"]:
            context += " (ENTRY POINT)"
        context += "\n"

        for cls in info["classes"][:3]:
            docstring = cls['docstring'][:60] if cls['docstring'] else ''
            context += f"   class {cls['name']}: {docstring}\n"
            for method in cls["methods"][:4]:
                context += f"      - {method['name']}()\n"

        for func in info["functions"][:4]:
            docstring = func['docstring'][:60] if func['docstring'] else ''
            context += f"   function {func['name']}(): {docstring}\n"

        context += "\n"

    context += "Dependencies:\n"
    for dep in list(analysis["dependencies"])[:60]:
        context += f"   {dep['from']} imports from {dep['to']}\n"

    prompt = f"""Based on this ACTUAL repository structure, write a clear architecture description.

{context}

Rules:
1. ONLY describe what you see in the structure above - no guessing
2. Explain the data flow from entry point through the modules
3. Be concise - max 5 bullet points
4. Mention specific file names and function names

Format:
## Overview
[1-2 sentence summary]

## Data Flow
1. [Step 1]
2. [Step 2]
...

## Key Components
- **[filename]**: [purpose]
"""

    response = llm.invoke(prompt)
    return response.content


def _path_to_id(path: str) -> str:
    """Convert file path to valid Mermaid node ID."""
    return path.replace("/", "_").replace(".", "_").replace("-", "_")

def generate_smart_diagram(analysis: dict) -> tuple[str, dict]:
    """Generate a professional architecture diagram using LLM analysis."""

    analyzer = ArchitectureAnalyzer()
    architecture = analyzer.analyze(analysis)
    diagram = generate_professional_diagram(architecture)

    return diagram, architecture


def generate_pyvis_diagram(files_analysis: dict, architecture: dict) -> str:
    """
    Generate an interactive Pyvis/vis.js diagram from the real import graph.
    Returns an HTML string that can be rendered via streamlit.components.v1.html().
    """
    net = Network(
        height="620px",
        width="100%",
        bgcolor="#0f0f1a",
        font_color="#e2e8f0",
        directed=True,
    )
    net.set_options("""{
      "physics": {
        "stabilization": {"iterations": 100},
        "barnesHut": {"gravitationalConstant": -8000, "springLength": 120}
      },
      "edges": {"arrows": {"to": {"enabled": true, "scaleFactor": 0.6}}, "color": {"color": "#4a5568"}},
      "nodes": {"font": {"size": 13}},
      "interaction": {"hover": true, "tooltipDelay": 200}
    }""")

    cluster_map: dict = architecture.get("_cluster_map", {})

    for file_path, info in files_analysis["files"].items():
        cid = cluster_map.get(file_path, 0)
        color = LAYER_COLORS[cid % len(LAYER_COLORS)]
        label = Path(file_path).name

        classes = [c["name"] for c in info.get("classes", [])]
        functions = [f["name"] for f in info.get("functions", [])]
        tooltip_lines = [f"<b>{file_path}</b>"]
        if classes:
            tooltip_lines.append(f"Classes: {', '.join(classes[:5])}")
        if functions:
            tooltip_lines.append(f"Functions: {', '.join(functions[:5])}")
        tooltip = "<br>".join(tooltip_lines)

        net.add_node(
            file_path,
            label=label,
            color=color,
            title=tooltip,
            size=18,
            borderWidth=2,
        )

    # Resolve import targets to actual file paths (same logic as build_graph)
    file_stems = {Path(f).stem: f for f in files_analysis["files"]}
    seen_edges: set = set()

    for dep in files_analysis.get("dependencies", []):
        src = dep["from"]
        module_base = dep["to"].split(".")[0]
        target = file_stems.get(module_base)
        if target and target != src and target in files_analysis["files"]:
            key = f"{src}→{target}"
            if key not in seen_edges:
                seen_edges.add(key)
                net.add_edge(src, target)

    return net.generate_html()
