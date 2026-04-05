# Architecture & Feature Plan

> This document is your single source of truth for what we're building, why, and how.
> Read it top to bottom once. After that, use it as a reference.

---

## Table of Contents

1. [What Are We Building?](#1-what-are-we-building)
2. [Where We Are Now vs Where We're Going](#2-where-we-are-now-vs-where-were-going)
3. [The Build Roadmap](#3-the-build-roadmap)
4. [Full System Architecture](#4-full-system-architecture)
5. [How a Chat Request Works](#5-how-a-chat-request-works)
6. [How Repo Indexing Works](#6-how-repo-indexing-works)
7. [How the Security Scanner Works](#7-how-the-security-scanner-works)
8. [Full Feature List](#8-full-feature-list)
9. [Tech Stack](#9-tech-stack)
10. [System Design Concepts You'll Learn](#10-system-design-concepts-youll-learn)

---

## 1. What Are We Building?

A tool for developers who **actively work on a codebase** — not just tourists reading it for the first time.

| | repomind.in (existing) | Our Project |
|---|---|---|
| **Angle** | "I'm new here, explain this repo to me" | "I work here every day, help me go deeper" |
| **Models** | Gemini only | OpenAI + local Ollama (free, offline) |
| **Approach** | Agentic file selection | RAG + Agentic hybrid |
| **Security** | Basic scanner | Deep scanner + fix suggestions |
| **Onboarding** | None | Guided walkthrough mode |
| **Health Dashboard** | None | Complexity, coverage, hotspot files |
| **PR Review** | None | GitHub Actions integration |

---

## 2. Where We Are Now vs Where We're Going

### Right Now (Streamlit, Phase 1 complete)

```
┌─────────────────────────────────┐
│         Streamlit App           │
│  (UI + business logic + AI,     │
│   all in one app.py)            │
└──────────────┬──────────────────┘
               │
        ┌──────┴──────┐
        │   ChromaDB  │
        │  (vectors)  │
        └─────────────┘
```

**The problem:** everything is jammed into one process. Can't scale, can't have auth, can't run background jobs, can't handle multiple users at once.

---

### Where We're Going (Phase 3 target)

```
        Browser / Mobile PWA
               │
    ┌──────────▼──────────┐
    │   React + Next.js   │  ← replaces Streamlit UI
    │   (Frontend)        │
    └──────────┬──────────┘
               │  HTTP (REST / WebSocket)
    ┌──────────▼──────────┐
    │   FastAPI Backend   │  ← replaces Streamlit logic
    │   /api/chat         │
    │   /api/index        │
    │   /api/scan         │
    └──┬───────────────┬──┘
       │               │
┌──────▼──────┐  ┌─────▼──────────────┐
│ PostgreSQL  │  │  Redis             │
│ (users,     │  │  (cache + queue)   │
│  repos,     │  └─────┬──────────────┘
│  history)   │        │ dequeue jobs
└─────────────┘  ┌─────▼──────────────┐
                 │  Celery Workers    │
                 │  - Indexer         │
                 │  - Scanner         │
                 │  - Health          │
                 └─────┬──────────────┘
                       │
                ┌──────▼──────┐
                │   ChromaDB  │  ← keep this, it works
                │  (vectors)  │
                └─────────────┘
```

**Why this is better:**
- React can do auth, real-time updates, interactive graphs — Streamlit can't
- FastAPI separates UI from logic — the API can be called by a CLI or GitHub Actions too
- PostgreSQL stores users, sessions, annotations — ChromaDB can't do that
- Celery + Redis run heavy jobs (indexing, scanning) in the background — the app stays responsive
- Workers run independently — one slow job doesn't block everything else

---

## 3. The Build Roadmap

```
Phase 1 — Foundation                                              ✅ DONE
  Tests · CI (GitHub Actions) · Error Handling · Linting · Branch Protection

Phase 2 — Features on Streamlit                                   ← WE ARE HERE
  Goal: prove the features work BEFORE rebuilding the architecture
  ├── Rename the project                                           ← do this first
  ├── Security Scanner (OSV.dev + AI)                             ← start here
  ├── Onboarding Mode (guided walkthrough)
  ├── Real-time Transparency (show which files AI reads)
  └── Local Model Support (Ollama — free + offline)

Phase 3 — Real Architecture
  Goal: move off Streamlit onto proper foundation
  ├── FastAPI backend (migrate all logic from app.py)
  ├── React + Next.js frontend
  ├── PostgreSQL + GitHub OAuth auth
  ├── Celery + Redis (background jobs)
  └── Docker Compose (run everything with one command)

Phase 4 — Advanced Features
  Goal: differentiate completely
  ├── Codebase Health Dashboard (complexity, test coverage, hotspots)
  ├── PR Review Bot (GitHub webhook auto-comments)
  ├── Multi-repo support (ask questions across repos)
  ├── Team Annotations (pin notes on files)
  ├── Interactive Code Map (D3.js clickable graph)
  └── Cloud Deploy (Vercel + Railway)
```

---

## 4. Full System Architecture

> This shows every component in the final system and how they connect.
> Don't be intimidated — you'll build this one piece at a time.

```mermaid
graph TB
    %% CLIENT LAYER
    subgraph CLIENT["🌐 Client Layer"]
        direction LR
        Browser["Browser"]
        PWA["Mobile PWA"]
    end

    %% FRONTEND
    subgraph FRONTEND["⚛️ Frontend — React + Next.js"]
        direction TB
        ChatUI["💬 Chat Interface"]
        OnboardUI["🎓 Onboarding Mode"]
        ArchUI["🏗️ Architecture Viewer (D3.js)"]
        SecurityUI["🔒 Security Dashboard"]
        HealthUI["📊 Health Dashboard"]
        AnnotUI["📌 Team Annotations"]
        PRReviewUI["🔍 PR Review"]
    end

    %% BACKEND
    subgraph BACKEND["⚡ Backend — FastAPI"]
        direction TB
        Gateway["🚪 API Gateway (auth + rate limiting + routing)"]

        subgraph ROUTES["API Routes"]
            direction LR
            ChatRoute["POST /api/chat"]
            IndexRoute["POST /api/index"]
            ScanRoute["POST /api/scan"]
            HealthRoute["GET /api/health"]
            OnboardRoute["GET /api/onboard"]
            PRRoute["POST /api/pr-review"]
            AnnotRoute["POST /api/annotate"]
        end
    end

    %% BACKGROUND WORKERS
    subgraph WORKERS["⚙️ Background Workers — Celery"]
        direction TB
        IndexWorker["🔄 Indexer Worker — clone → parse → embed → store"]
        ScanWorker["🔒 Scanner Worker — OSV.dev + AI analysis"]
        HealthWorker["📊 Health Worker — git metrics + complexity"]
        DiagramWorker["🏗️ Diagram Worker — architecture analysis"]
    end

    %% DATA LAYER
    subgraph DATA["💾 Data Layer"]
        direction TB
        PostgreSQL[("🐘 PostgreSQL — users, repos, sessions, annotations, scan results")]
        ChromaDB[("🔮 ChromaDB — code embeddings, vector index")]
        Redis[("⚡ Redis — API cache, task queue, session store, rate limits")]
    end

    %% EXTERNAL SERVICES
    subgraph EXTERNAL["🌍 External APIs"]
        direction TB
        OpenAI["🤖 OpenAI — GPT-4o-mini (answers) + embeddings"]
        Ollama["🦙 Ollama — Llama 3 / CodeLlama (free, offline)"]
        GithubAPI["🐙 GitHub API — repo tree, files, commits, PRs"]
        OSVDev["🛡️ OSV.dev — open vulnerability database (free)"]
        BlobStorage["☁️ Cloudflare R2 — repos, reports, diagram exports"]
    end

    %% DEVOPS
    subgraph CICD["🔧 DevOps"]
        direction LR
        GHActions["⚙️ GitHub Actions — test + lint + deploy on every push"]
        DockerCompose["🐳 Docker Compose — one command local dev"]
    end

    CLIENT --> FRONTEND
    FRONTEND --> Gateway
    Gateway --> ROUTES

    IndexRoute -->|"enqueue job"| Redis
    ScanRoute -->|"enqueue job"| Redis
    ChatRoute --> ChromaDB
    ChatRoute --> Redis

    Redis -->|"dequeue"| IndexWorker
    Redis -->|"dequeue"| ScanWorker
    Redis -->|"dequeue"| HealthWorker

    IndexWorker --> GithubAPI
    IndexWorker --> ChromaDB
    IndexWorker --> BlobStorage
    IndexWorker --> PostgreSQL

    ScanWorker --> OSVDev
    ScanWorker --> OpenAI
    ScanWorker --> PostgreSQL

    HealthWorker --> GithubAPI
    HealthWorker --> PostgreSQL

    ChatRoute --> OpenAI
    ChatRoute --> Ollama

    Gateway --> PostgreSQL
    AnnotRoute --> PostgreSQL

    GHActions -->|"runs on push"| DockerCompose
```

---

## 5. How a Chat Request Works

> Step by step — what actually happens between you typing a question and seeing an answer.

**The key ideas here:**
- We first check the **cache** — if someone asked the same question before, return instantly
- We **reformulate** the question using chat history (so follow-up questions make sense)
- We search **ChromaDB** for the most relevant code chunks (this is the RAG part)
- The answer **streams back word by word** like ChatGPT — no waiting for the full response

```mermaid
sequenceDiagram
    actor User
    participant React as React Frontend
    participant FastAPI as FastAPI Backend
    participant Redis as Redis Cache
    participant Reformulator as Query Reformulator
    participant ChromaDB as ChromaDB (Vector Store)
    participant LLM as OpenAI / Ollama

    User->>React: types "how does the parser work?"
    React->>FastAPI: POST /api/chat { query, repo_id, history }

    FastAPI->>Redis: check cache (query + repo_id key)
    Redis-->>FastAPI: cache MISS

    FastAPI->>Reformulator: reformulate(query, chat_history)
    Note over Reformulator: uses last 6 messages to make<br/>the question standalone
    Reformulator-->>FastAPI: "how does the code parser work in this repo?"

    FastAPI->>ChromaDB: similarity_search(reformulated_query, top_k=6)
    ChromaDB-->>FastAPI: 6 most relevant code chunks

    FastAPI->>LLM: generate(query, chunks, history)
    Note over LLM: streams response token by token

    LLM-->>React: streaming response (SSE)
    React-->>User: answer appears word by word ✨

    FastAPI->>Redis: cache(query_key, answer, TTL=1hr)
```

---

## 6. How Repo Indexing Works

> What happens when you paste a GitHub URL and click "Index".

**The key idea:** indexing is slow (clone + parse + embed can take minutes for big repos).
So we **don't block the UI**. We immediately say "job started!" and hand the work to a background worker.
The UI gets notified via WebSocket when it's done.

```mermaid
sequenceDiagram
    actor User
    participant React as React Frontend
    participant FastAPI as FastAPI Backend
    participant Redis as Redis Queue
    participant Worker as Celery Worker
    participant GitHub as GitHub API
    participant Parser as Parser (AST + Tree-sitter)
    participant Embedder as Embedder (OpenAI)
    participant ChromaDB as ChromaDB
    participant PostgreSQL as PostgreSQL

    User->>React: pastes "https://github.com/user/repo"
    React->>FastAPI: POST /api/index { url }
    FastAPI->>PostgreSQL: INSERT repo (url, status="queued")
    FastAPI->>Redis: enqueue("index_repo", repo_id)
    FastAPI-->>React: { job_id: "abc123", status: "queued" }
    React-->>User: "Indexing started! We'll notify you when done."

    Note over Worker: runs independently in background
    Redis->>Worker: dequeue job
    Worker->>GitHub: clone repo / fetch file tree
    GitHub-->>Worker: all source files

    loop for each file
        Worker->>Parser: parse(file_content, extension)
        Parser-->>Worker: chunks (functions, classes, blocks)
    end

    Worker->>Embedder: embed(all_chunks)
    Embedder-->>Worker: vectors (float arrays)

    Worker->>ChromaDB: store(vectors, metadata)
    Worker->>PostgreSQL: UPDATE repo (status="ready", chunks=1234)

    Worker-->>React: WebSocket event: "repo_ready"
    React-->>User: "Ready! Ask your first question."
```

---

## 7. How the Security Scanner Works

> How we find vulnerabilities in a repo using OSV.dev (free, open vulnerability database) + AI.

**The key idea:** three parallel scans — dependencies, code patterns, configs — then an AI layer filters out false positives before showing you anything.

```mermaid
flowchart TD
    A["User clicks 'Scan for Vulnerabilities'"] --> B["FastAPI enqueues scan job"]
    B --> C["Celery Scanner Worker starts"]

    C --> D["Fetch repo files from ChromaDB / disk"]
    D --> E["Filter into 3 file categories"]

    E --> F1["Dependency files\n(requirements.txt, package.json)"]
    E --> F2["Code files\n(.py, .js, .ts)"]
    E --> F3["Config files\n(.env.example, docker-compose.yml)"]

    F1 --> G["Query OSV.dev API\nfor known CVEs in each dependency"]
    F2 --> H["Pattern scan\n(regex for SQL injection, XSS,\nhardcoded secrets, credentials)"]
    F3 --> I["Config analysis\n(exposed ports, weak settings)"]

    G --> J["AI Verification Layer\n(OpenAI filters false positives)"]
    H --> J
    I --> J

    J --> K{"Confidence > 80%?"}
    K -->|Yes| L["Add to findings"]
    K -->|No| M["Discard — false positive"]

    L --> N["Risk scoring\nCritical / High / Medium / Low"]
    N --> O["Store in PostgreSQL"]
    O --> P["Send to React dashboard"]
    P --> Q["User sees: file · line · severity · fix suggestion"]
```

---

## 8. Full Feature List

### Phase 2 — Building now (on Streamlit)

| Feature | What it does | How |
|---|---|---|
| **Security Scanner** | Find CVEs in dependencies, secrets in code | OSV.dev API + regex + OpenAI |
| **Onboarding Mode** | Guided walkthrough — entry points, reading order, glossary | LLM chaining |
| **Real-time Transparency** | Show which files AI picked and why | SSE streaming |
| **Local Model Support** | Use Ollama instead of OpenAI — free, offline | Ollama API |
| **Basic Health Metrics** | Git stats, file complexity overview | git log analysis |

### Phase 3 — Architecture rebuild

| Feature | What it does | How |
|---|---|---|
| **Background Indexing** | Index large repos without freezing the UI | Celery + Redis |
| **Response Caching** | Same question = instant answer | Redis TTL cache |
| **User Auth** | Login with GitHub, save your indexed repos | NextAuth / JWT |
| **Persistent History** | Save all chat conversations | PostgreSQL |
| **Streaming Responses** | Answers appear word by word | Server-Sent Events |
| **Rate Limiting** | Fair use — anonymous vs authenticated tiers | Redis counters |

### Phase 4 — Advanced

| Feature | What it does | How |
|---|---|---|
| **Interactive Code Map** | Clickable, zoomable graph of the codebase | D3.js / Cytoscape |
| **PR Review Bot** | Auto-comments on pull requests | GitHub Webhooks |
| **Health Dashboard** | Complexity, test coverage, hotspot files, bus factor | git log analysis |
| **Team Annotations** | Pin notes on files — tribal knowledge layer | PostgreSQL |
| **Multi-repo Support** | Ask questions across multiple repos | ChromaDB collections |
| **Blast Radius View** | "If I change this file, what breaks?" | Dependency graph |
| **Living Documentation** | Auto-generated docs, updated on every push | CI/CD + LLM |

---

## 9. Tech Stack

| Layer | Technology | Why we chose it |
|---|---|---|
| **Frontend** | React + Next.js | Industry standard. Streamlit can't do auth, real-time, or interactive graphs |
| **Backend** | FastAPI (Python) | Fast, async, auto-generates API docs. You already know Python |
| **AI — Cloud** | OpenAI GPT-4o-mini | Best quality answers, simple API |
| **AI — Local** | Ollama + Llama 3 | Free, runs on your machine, no internet needed — our differentiator |
| **Vector DB** | ChromaDB | Already built in, works great for code search |
| **Relational DB** | PostgreSQL | Best SQL DB. Free tier on Neon. Stores users, repos, history |
| **Cache + Queue** | Redis | Industry standard for both caching and task queues |
| **Task Queue** | Celery | Python-native worker system, plugs directly into Redis |
| **Security** | OSV.dev API | Free, open, comprehensive CVE database |
| **Auth** | GitHub OAuth + JWT | Users already have GitHub accounts |
| **File Storage** | Cloudflare R2 | Cheaper than AWS S3, same API |
| **CI/CD** | GitHub Actions | Already set up in Phase 1 |
| **Deploy** | Docker + Vercel/Railway | Containers for backend, managed hosting for frontend |
| **Diagrams** | Mermaid.js + D3.js | Mermaid for static diagrams, D3 for interactive code maps |

---

## 10. System Design Concepts You'll Learn

Every concept here is something you'll actually implement — not just read about.

| Concept | Where you'll build it |
|---|---|
| **Caching** | Redis for API responses (TTL 1hr) + ChromaDB as index cache |
| **Message Queue** | Redis + Celery: indexing jobs run in background, UI stays fast |
| **Load Balancing** | Multiple FastAPI + Celery worker instances (Phase 3) |
| **API Gateway** | FastAPI: routing, auth middleware, rate limiting |
| **SQL + NoSQL** | PostgreSQL (structured data) + ChromaDB (vector data) |
| **Event-Driven** | "repo indexed" → trigger security scan → notify user |
| **CAP Theorem** | Answer with partial index while still indexing (availability > consistency) |
| **Streaming** | Server-Sent Events for word-by-word AI responses |
| **Microservices** | Separate indexer/scanner/chat services (Phase 4) |
| **Blob Storage** | Cloudflare R2 for cloned repos, reports, diagram exports |
| **CDN** | Vercel serves frontend JS/CSS from nearest server globally |
| **Pub/Sub** | WebSocket: worker notifies UI when indexing job finishes |
| **Consistent Hashing** | ChromaDB sharding across nodes (Phase 4) |
| **Data Redundancy** | PostgreSQL daily backups + ChromaDB snapshots to R2 |

---

> **Next step:** Pick a project name, then we start Phase 2 with the Security Scanner.
