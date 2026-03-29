import os

import streamlit as st
import streamlit.components.v1 as components

from analysis.dependency_parser import analyze_repo
from analysis.diagram_generator import (
    generate_architecture_description,
    generate_smart_diagram,
)
from generation.generator import Generator
from ingestion.embedder import create_vector_store
from ingestion.loader import load_repo
from ingestion.parser import parse_all_files
from retrieval.reformulator import QueryReformulator
from retrieval.retriever import Retriever

# Page config
st.set_page_config(
    page_title="RepoMind",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
        font-family: 'Inter', sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 3rem;
        font-weight: 700;
        text-align: center;
        padding: 1rem 0;
    }
    
    .sub-header {
        color: #8892b0;
        text-align: center;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 20px 20px 5px 20px;
        margin: 0.5rem 0;
        max-width: 80%;
        margin-left: auto;
    }
    
    .assistant-message {
        background: rgba(255, 255, 255, 0.08);
        color: #e2e8f0;
        padding: 1rem 1.5rem;
        border-radius: 20px 20px 20px 5px;
        margin: 0.5rem 0;
        max-width: 80%;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .source-card {
        background: rgba(102, 126, 234, 0.1);
        border: 1px solid rgba(102, 126, 234, 0.3);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin: 0.25rem 0;
        font-family: monospace;
        font-size: 0.85rem;
        color: #a5b4fc;
    }
    
    [data-testid="stSidebar"] {
        background: rgba(15, 15, 26, 0.95);
    }
    
    .arch-description {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 1.5rem;
        color: #cbd5e1;
        line-height: 1.8;
    }
</style>
""", unsafe_allow_html=True)

def render_mermaid(mermaid_code: str):
    """Render Mermaid diagram with export functionality."""

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
        <style>
            body {{
                background-color: #0f0f1a;
                margin: 0;
                padding: 20px;
                display: flex;
                flex-direction: column;
                align-items: center;
            }}
            .controls {{
                margin-bottom: 15px;
                display: flex;
                gap: 10px;
            }}
            .export-btn {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .export-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
            }}
            .mermaid {{
                width: 100%;
            }}
            .mermaid svg {{
                width: 100%;
                height: auto;
                max-height: 600px;
            }}
        </style>
    </head>
    <body>
        <div class="controls">
            <button class="export-btn" onclick="exportPNG()">📥 Export as PNG</button>
            <button class="export-btn" onclick="exportSVG()">📥 Export as SVG</button>
        </div>
        <div class="mermaid" id="diagram">
{mermaid_code}
        </div>
        <script>
            mermaid.initialize({{
                startOnLoad: true,
                theme: 'dark',
                themeVariables: {{
                    'primaryColor': '#667eea',
                    'primaryTextColor': '#ffffff',
                    'primaryBorderColor': '#764ba2',
                    'lineColor': '#8892b0',
                    'secondaryColor': '#1a1a2e',
                    'background': 'transparent',
                    'fontSize': '14px',
                    'clusterBkg': 'rgba(102, 126, 234, 0.1)',
                    'clusterBorder': '#667eea'
                }},
                flowchart: {{
                    htmlLabels: true,
                    curve: 'basis',
                    nodeSpacing: 50,
                    rankSpacing: 80,
                    padding: 20
                }}
            }});
            
            function exportSVG() {{
                const svg = document.querySelector('.mermaid svg');
                if (!svg) {{
                    alert('Diagram not ready yet. Please wait a moment.');
                    return;
                }}
                
                const svgClone = svg.cloneNode(true);
                svgClone.style.backgroundColor = '#0f0f1a';
                
                const svgData = new XMLSerializer().serializeToString(svgClone);
                const blob = new Blob([svgData], {{ type: 'image/svg+xml' }});
                const url = URL.createObjectURL(blob);
                
                const a = document.createElement('a');
                a.href = url;
                a.download = 'architecture-diagram.svg';
                a.click();
                URL.revokeObjectURL(url);
            }}
            
            function exportPNG() {{
                const svg = document.querySelector('.mermaid svg');
                if (!svg) {{
                    alert('Diagram not ready yet. Please wait a moment.');
                    return;
                }}
                
                const bbox = svg.getBoundingClientRect();
                const width = Math.ceil(bbox.width * 2);
                const height = Math.ceil(bbox.height * 2);
                
                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                
                ctx.fillStyle = '#0f0f1a';
                ctx.fillRect(0, 0, width, height);
                
                // Clone SVG and prepare for conversion
                const svgClone = svg.cloneNode(true);
                svgClone.setAttribute('width', width);
                svgClone.setAttribute('height', height);
                
                // Add xmlns if missing
                if (!svgClone.getAttribute('xmlns')) {{
                    svgClone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
                }}
                
                // Serialize SVG
                const svgData = new XMLSerializer().serializeToString(svgClone);
                
                // Encode as base64 data URI (avoids CORS issues)
                const base64Data = btoa(unescape(encodeURIComponent(svgData)));
                const dataUri = 'data:image/svg+xml;base64,' + base64Data;
                
                const img = new Image();
                img.onload = function() {{
                    ctx.drawImage(img, 0, 0, width, height);
                    
                    canvas.toBlob(function(blob) {{
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'architecture-diagram.png';
                        a.click();
                        URL.revokeObjectURL(url);
                    }}, 'image/png');
                }};
                
                img.onerror = function() {{
                    alert('PNG export failed. Please use SVG export instead.');
                }};
                
                img.src = dataUri;
            }}
        </script>
    </body>
    </html>
    """
    components.html(html_content, height=700, scrolling=True)


# Header
st.markdown('<h1 class="main-header">🧠 RepoMind</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Chat with any codebase • Understand architecture instantly</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 📦 Load Repository")

    repo_url = st.text_input("GitHub URL", placeholder="https://github.com/user/repo", label_visibility="collapsed")

    if st.button("🚀 Load & Index", type="primary", use_container_width=True):
        if repo_url:
            with st.status("Processing...", expanded=True) as status:
                st.write("Cloning repository...")
                files = load_repo(repo_url)

                st.write(f"Parsing {len(files)} files...")
                chunks = parse_all_files(files)

                st.write(f"Embedding {len(chunks)} chunks...")
                repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
                create_vector_store(chunks, collection_name=repo_name)

                status.update(label="✅ Done!", state="complete")

            st.session_state["repo_name"] = repo_name
            st.session_state["repo_path"] = f"repos/{repo_name}"
            st.session_state["chat_history"] = []
            st.rerun()

    st.markdown("---")
    st.markdown("### 📚 Indexed Repos")

    if os.path.exists("storage"):
        repos = [d for d in os.listdir("storage") if os.path.isdir(os.path.join("storage", d))]
        for repo in repos:
            if st.button(f"📁 {repo}", key=f"repo_{repo}", use_container_width=True):
                st.session_state["repo_name"] = repo
                st.session_state["repo_path"] = f"repos/{repo}"
                st.session_state["chat_history"] = []
                st.rerun()


# Main content
if "repo_name" in st.session_state:
    # Initialize components
    if "retriever" not in st.session_state or st.session_state.get("current_repo") != st.session_state["repo_name"]:
        st.session_state["retriever"] = Retriever(st.session_state["repo_name"])
        st.session_state["reformulator"] = QueryReformulator()
        st.session_state["generator"] = Generator()
        st.session_state["current_repo"] = st.session_state["repo_name"]

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Tabs
    tab1, tab2 = st.tabs(["💬 Chat", "🏗️ Architecture"])

    with tab1:
        st.info(f"💬 Chatting with: **{st.session_state['repo_name']}**")

        # Chat history
        for msg in st.session_state["chat_history"]:
            if msg["role"] == "user":
                st.markdown(f'<div class="user-message">{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="assistant-message">{msg["content"]}</div>', unsafe_allow_html=True)
                if "sources" in msg and msg["sources"]:
                    with st.expander("📌 View Sources"):
                        for src in msg["sources"]:
                            st.markdown(f'<div class="source-card">{src["file"]} → {src["name"]} (lines {src["lines"]})</div>', unsafe_allow_html=True)

        # Chat input
        if query := st.chat_input("Ask anything about the codebase..."):
            st.session_state["chat_history"].append({"role": "user", "content": query})

            with st.spinner("Thinking..."):
                reformulated = st.session_state["reformulator"].reformulate(
                    query,
                    st.session_state["chat_history"][:-1]
                )
                chunks = st.session_state["retriever"].search(reformulated)
                response = st.session_state["generator"].generate(
                    reformulated,
                    chunks,
                    st.session_state["chat_history"][:-1]
                )

            st.session_state["chat_history"].append({
                "role": "assistant",
                "content": response["answer"],
                "sources": response["sources"]
            })
            st.rerun()

    with tab2:
        st.info(f"🏗️ Architecture for: **{st.session_state['repo_name']}**")

        if st.button("🔍 Analyze Architecture", type="primary"):
            repo_path = st.session_state.get("repo_path", f"repos/{st.session_state['repo_name']}")

            if os.path.exists(repo_path):
                with st.spinner("🧠 Analyzing codebase structure..."):
                    analysis = analyze_repo(repo_path)
                    st.session_state["analysis"] = analysis

                with st.spinner("🎨 Generating professional diagram..."):
                    diagram, architecture = generate_smart_diagram(analysis)
                    st.session_state["flowchart"] = diagram
                    st.session_state["architecture"] = architecture
                    st.session_state["description"] = generate_architecture_description(analysis)
            else:
                st.error("Repository not found. Please re-index.")

        if all(key in st.session_state for key in ["flowchart", "description", "architecture"]):
            st.markdown("### 📊 Architecture Diagram")
            render_mermaid(st.session_state["flowchart"])

            st.markdown("---")

            col1, col2 = st.columns([1, 1])

            with col1:
                st.markdown("### 📝 Architecture Overview")
                st.markdown(f'<div class="arch-description">{st.session_state["description"]}</div>', unsafe_allow_html=True)

            with col2:
                st.markdown("### 🔗 External Services")
                if "architecture" in st.session_state:
                    for svc in st.session_state["architecture"].get("external_services", []):
                        icon = "🧠" if svc["type"] == "ai" else "🗄️" if svc["type"] == "database" else "☁️"
                        st.markdown(f"""
                        <div class="glass-card" style="padding: 0.75rem;">
                            {icon} <strong>{svc['name']}</strong>
                        </div>
                        """, unsafe_allow_html=True)

            # Layer breakdown
            st.markdown("### 🏛️ Architecture Layers")
            if "architecture" in st.session_state:
                for layer in st.session_state["architecture"].get("layers", []):
                    with st.expander(f"📁 {layer['name']}", expanded=True):
                        cols = st.columns(3)
                        for i, comp in enumerate(layer.get("components", [])):
                            with cols[i % 3]:
                                st.markdown(f"""
                                <div class="glass-card">
                                    <div style="font-weight: 600; color: #a5b4fc;">{comp['name']}</div>
                                    <div style="color: #8892b0; font-size: 0.8rem;">{comp['description']}</div>
                                    <div style="color: #667eea; font-size: 0.75rem; margin-top: 0.5rem;">📄 {comp['file']}</div>
                                </div>
                                """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="text-align: center; padding: 4rem 2rem;">
        <div class="glass-card" style="max-width: 600px; margin: 0 auto;">
            <h2 style="color: #a5b4fc;">Welcome to RepoMind</h2>
            <p style="color: #8892b0;">
                Load any GitHub repository and chat with the codebase.<br>
                Ask questions and understand architecture with AI.
            </p>
            <p style="color: #667eea; margin-top: 2rem;">
                👈 Paste a GitHub URL in the sidebar to start
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
