"""
AutoPR - Autonomous Issue-to-Pull Request Development System
Main FastAPI application entry point
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
import asyncio

from agents.issue_interpreter import IssueInterpreter
from agents.codebase_analyzer import CodebaseAnalyzer
from agents.code_generator import CodeChangeGenerator
from agents.pr_manager import PullRequestManager
from agents.code_reviewer import AutomatedCodeReviewer
from core.pipeline import AutoPRPipeline

app = FastAPI(
    title="AutoPR - Autonomous PR System",
    description="Converts GitHub issues into pull requests automatically using AI",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / Response Models ──────────────────────────────────────────────────

class IssueRequest(BaseModel):
    issue_title: str
    issue_body: str
    repo_owner: Optional[str] = "demo-org"
    repo_name: Optional[str] = "demo-repo"
    github_token: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    use_real_github: bool = False

class PipelineResponse(BaseModel):
    success: bool
    pipeline_id: str
    stages: dict
    pull_request: Optional[dict] = None
    review: Optional[dict] = None

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "AutoPR System Online", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "components": ["interpreter", "analyzer", "generator", "pr_manager", "reviewer"]}

@app.post("/api/run-pipeline")
async def run_pipeline(request: IssueRequest):
    """
    Main endpoint: runs the full AutoPR pipeline for a given issue.
    Returns structured results from each stage.
    """
    pipeline = AutoPRPipeline(
        anthropic_api_key=request.anthropic_api_key,
        github_token=request.github_token,
        use_real_github=request.use_real_github
    )

    try:
        result = await pipeline.run(
            issue_title=request.issue_title,
            issue_body=request.issue_body,
            repo_owner=request.repo_owner,
            repo_name=request.repo_name,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stream-pipeline")
async def stream_pipeline(request: IssueRequest):
    """
    Streaming endpoint: emits Server-Sent Events for real-time pipeline progress.
    """
    pipeline = AutoPRPipeline(
        anthropic_api_key=request.anthropic_api_key,
        github_token=request.github_token,
        use_real_github=request.use_real_github
    )

    async def event_generator():
        async for event in pipeline.run_streaming(
            issue_title=request.issue_title,
            issue_body=request.issue_body,
            repo_owner=request.repo_owner,
            repo_name=request.repo_name,
        ):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/demo-issue")
async def get_demo_issue():
    """Returns a pre-built demo issue for quick demonstration."""
    return {
        "issue_title": "Fix login bug when password field is empty",
        "issue_body": """## Bug Report

**Description:**
When a user submits the login form with an empty password field, the application crashes 
with an unhandled exception instead of showing a validation error.

**Steps to Reproduce:**
1. Navigate to /login
2. Enter a valid username
3. Leave password field empty
4. Click "Submit"

**Expected Behavior:**
A user-friendly error message: "Password cannot be empty"

**Actual Behavior:**
Application throws a 500 Internal Server Error. The traceback shows:
```
AttributeError: 'NoneType' object has no attribute 'encode'
  File "auth/login.py", line 47, in validate_password
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
```

**Environment:**
- Python 3.11
- Flask 3.0
- bcrypt 4.1

**Additional Context:**
This affects all login flows. Priority: HIGH
""",
        "repo_owner": "acme-corp",
        "repo_name": "web-platform"
    }
