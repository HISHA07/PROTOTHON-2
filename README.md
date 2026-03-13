# ⚡ AutoPR — Autonomous Issue-to-Pull Request System

> Transform a GitHub issue into a reviewed Pull Request in seconds using AI.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AutoPR System                            │
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   │
│  │  Issue   │──▶│Codebase  │──▶│  Code    │──▶│   PR     │   │
│  │Interpret │   │Analyzer  │   │Generator │   │ Manager  │   │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   │
│       │               │              │               │          │
│       └───────────────┴──────────────┴───────────────┘          │
│                                     │                           │
│                              ┌──────────┐                       │
│                              │Automated │                       │
│                              │ Reviewer │                       │
│                              └──────────┘                       │
└─────────────────────────────────────────────────────────────────┘

Frontend (HTML/CSS/JS) ◄──► FastAPI Backend ◄──► Claude API
                                   │
                            GitHub REST API
                          (real or simulated)
```

## 📁 Project Structure

```
autopr/
├── backend/
│   ├── main.py                 # FastAPI app, routes
│   ├── requirements.txt
│   ├── core/
│   │   └── pipeline.py         # Pipeline orchestrator
│   └── agents/
│       ├── issue_interpreter.py  # Agent 1: Parse & classify issue
│       ├── codebase_analyzer.py  # Agent 2: Find relevant files
│       ├── code_generator.py     # Agent 3: Generate code fixes
│       ├── pr_manager.py         # Agent 4: Create pull request
│       └── code_reviewer.py      # Agent 5: Automated review
└── frontend/
    └── index.html              # Single-file dashboard
```

## 🚀 Quick Start

### Option A: Frontend Only (Demo Mode — Zero Setup)
```bash
# Just open the HTML file in your browser
open frontend/index.html
# Click "Load Demo Issue" then "Run AutoPR Pipeline"
```
Works immediately with realistic simulated data. No API key needed.

### Option B: Full Backend + Real AI

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Start the API server
uvicorn main:app --reload --port 8000

# 3. Open frontend in browser
open ../frontend/index.html

# 4. (Optional) Enter your Anthropic API key in the UI
#    to use real Claude AI instead of demo mode
```

## 🔑 API Key

Get a free key at: https://console.anthropic.com

**Without a key**: AutoPR uses realistic pre-built demo responses  
**With a key**: Claude interprets, generates code, and reviews in real time

## 🎬 Demo Scenario

The included demo models this real-world bug:

**Issue**: "Fix login bug when password field is empty"

**Pipeline output**:
1. 📝 **Interpreted** → `bug_fix`, priority: `high`, affects: `auth/login.py`
2. 🔍 **Analyzed** → Scanned 6 files, found 3 relevant (scores: 95%, 75%, 55%)
3. ⚙️ **Generated** → +36 lines / -7 lines across 3 files with before/after diffs
4. 🚀 **PR Created** → `#247 fix: add password validation to login handler`
5. ✅ **Reviewed** → Score: 82/100, APPROVED_WITH_SUGGESTIONS

## 🔌 API Endpoints

```
POST /api/run-pipeline       # Full pipeline, returns JSON
POST /api/stream-pipeline    # Real-time SSE stream
GET  /api/demo-issue         # Returns demo issue
GET  /health                 # Health check
GET  /docs                   # Swagger UI
```

## 🧩 Component Details

| Agent | Input | Output |
|-------|-------|--------|
| `IssueInterpreter` | Issue title + body | task_type, keywords, file_hints |
| `CodebaseAnalyzer` | Interpretation | Ranked file list with relevance scores |
| `CodeChangeGenerator` | Interpretation + file context | Before/after diffs per file |
| `PullRequestManager` | Changes | PR object (real or simulated) |
| `AutomatedCodeReviewer` | Changes + PR | Structured review with scores |

## 🛠️ Tech Stack

- **Backend**: Python 3.11+ · FastAPI · Uvicorn
- **AI**: Anthropic Claude claude-sonnet-4-20250514
- **Frontend**: Vanilla HTML/CSS/JS (zero dependencies)
- **GitHub**: REST API v2022-11-28 (or simulation)
- **Parsing**: Python AST + keyword matching

## ⚡ Features

- ✅ Real-time pipeline with streaming SSE
- ✅ Works fully offline in demo mode
- ✅ Real Claude AI when API key provided
- ✅ Before/after code diff viewer
- ✅ GitHub API integration (optional)
- ✅ Structured review with category scores
- ✅ Security-aware (flags user enumeration, rate limiting)
- ✅ Impressive hackathon-ready UI
