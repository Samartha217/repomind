# 🧠 RepoMind

AI-powered codebase Q&A and architecture visualization tool. Chat with any GitHub repository and instantly understand its architecture.

## ✨ Features

- **💬 Chat with any codebase** — Ask questions about code in natural language
- **🏗️ Architecture visualization** — Auto-generate professional architecture diagrams
- **🔍 Smart code parsing** — AST-based chunking for Python files
- **📌 Source citations** — Every answer includes file paths and line numbers
- **📥 Export diagrams** — Download architecture diagrams as PNG/SVG

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit |
| Vector DB | ChromaDB |
| Embeddings | OpenAI text-embedding-3-small |
| LLM | GPT-4o-mini |
| Code Parsing | Python AST |
| Diagrams | Mermaid.js |

## 🏗️ Architecture
```
INGESTION PIPELINE (one-time per repo):
GitHub URL → LOADER → PARSER → EMBEDDER → ChromaDB

QUERY PIPELINE (every question):
Question → REFORMULATOR → RETRIEVER → CONTEXT BUILDER → GENERATOR → Answer

ARCHITECTURE ANALYSIS:
Repo → DEPENDENCY PARSER → ARCHITECTURE ANALYZER → DIAGRAM GENERATOR
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key

### Installation

1. **Clone the repository**
```bash
   git clone https://github.com/Samartha217/repomind.git
   cd repomind
```

2. **Create virtual environment**
```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
   pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
```

5. **Run the app**
```bash
   streamlit run app.py
```

6. **Open in browser**
```
   http://localhost:8501
```

## 📖 Usage

1. Paste a GitHub repository URL in the sidebar
2. Click "Load & Index" and wait for processing
3. **Chat tab:** Ask questions about the codebase
4. **Architecture tab:** Generate and export architecture diagrams

## 📁 Project Structure
```
repomind/
├── app.py                  # Streamlit UI
├── config.py               # Configuration
├── requirements.txt        # Dependencies
│
├── ingestion/              # Data ingestion pipeline
│   ├── loader.py           # Clone repos, read files
│   ├── parser.py           # AST parsing, chunking
│   └── embedder.py         # Vector embeddings
│
├── retrieval/              # Query processing
│   ├── retriever.py        # Vector search
│   ├── reformulator.py     # Query rewriting
│   └── context_builder.py  # Format context for LLM
│
├── generation/             # Response generation
│   └── generator.py        # LLM response generation
│
└── analysis/               # Architecture analysis
    ├── dependency_parser.py
    ├── architecture_analyzer.py
    └── diagram_generator.py
```

## 🔮 Future Improvements

- [ ] Tree-sitter universal parser (JS, TS, Java, Go support)
- [ ] Hybrid search (semantic + keyword)
- [ ] Reranking with cross-encoder
- [ ] Auto README generation
- [ ] PR review mode

## 📄 License

MIT License

## 👨‍💻 Author

**Samartha Deshpande** - [GitHub](https://github.com/Samartha217)