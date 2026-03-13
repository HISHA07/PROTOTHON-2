"""
AutoPR Pipeline Orchestrator
Coordinates all agents in sequence: Interpret → Analyze → Generate → PR → Review
"""

import asyncio
import uuid
import time
from typing import AsyncIterator, Optional
from agents.issue_interpreter import IssueInterpreter
from agents.codebase_analyzer import CodebaseAnalyzer
from agents.code_generator import CodeChangeGenerator
from agents.pr_manager import PullRequestManager
from agents.code_reviewer import AutomatedCodeReviewer


class AutoPRPipeline:
    """
    Orchestrates the full AutoPR workflow across 5 stages:
    1. Issue Interpretation
    2. Codebase Analysis
    3. Code Change Generation
    4. Pull Request Creation
    5. Automated Code Review
    """

    def __init__(self, anthropic_api_key: Optional[str] = None,
                 github_token: Optional[str] = None,
                 use_real_github: bool = False):
        self.pipeline_id = str(uuid.uuid4())[:8]
        self.anthropic_api_key = anthropic_api_key
        self.github_token = github_token
        self.use_real_github = use_real_github

        # Instantiate all agents
        self.interpreter = IssueInterpreter(api_key=anthropic_api_key)
        self.analyzer = CodebaseAnalyzer()
        self.generator = CodeChangeGenerator(api_key=anthropic_api_key)
        self.pr_manager = PullRequestManager(
            github_token=github_token,
            use_real_github=use_real_github
        )
        self.reviewer = AutomatedCodeReviewer(api_key=anthropic_api_key)

    async def run(self, issue_title: str, issue_body: str,
                  repo_owner: str, repo_name: str) -> dict:
        """Run the full pipeline and return complete results."""
        results = {
            "pipeline_id": self.pipeline_id,
            "success": True,
            "stages": {}
        }

        # Stage 1: Interpret issue
        interpretation = await self.interpreter.interpret(issue_title, issue_body)
        results["stages"]["interpretation"] = interpretation

        # Stage 2: Analyze codebase
        analysis = await self.analyzer.analyze(interpretation, repo_owner, repo_name)
        results["stages"]["analysis"] = analysis

        # Stage 3: Generate code changes
        changes = await self.generator.generate(interpretation, analysis)
        results["stages"]["code_changes"] = changes

        # Stage 4: Create pull request
        pr = await self.pr_manager.create_pr(
            interpretation, changes, repo_owner, repo_name
        )
        results["stages"]["pull_request"] = pr
        results["pull_request"] = pr

        # Stage 5: Automated review
        review = await self.reviewer.review(interpretation, changes, pr)
        results["stages"]["review"] = review
        results["review"] = review

        return results

    async def run_streaming(self, issue_title: str, issue_body: str,
                            repo_owner: str, repo_name: str) -> AsyncIterator[dict]:
        """Run pipeline with streaming events for real-time UI updates."""

        yield {"stage": "start", "pipeline_id": self.pipeline_id, "message": "Pipeline started"}
        await asyncio.sleep(0.1)

        # Stage 1
        yield {"stage": "interpreting", "message": "Analyzing issue with AI...", "progress": 10}
        interpretation = await self.interpreter.interpret(issue_title, issue_body)
        yield {"stage": "interpreted", "data": interpretation, "progress": 20,
               "message": f"Issue classified as: {interpretation['task_type']}"}

        # Stage 2
        yield {"stage": "analyzing", "message": "Scanning repository codebase...", "progress": 30}
        analysis = await self.analyzer.analyze(interpretation, repo_owner, repo_name)
        yield {"stage": "analyzed", "data": analysis, "progress": 45,
               "message": f"Found {len(analysis['relevant_files'])} relevant files"}

        # Stage 3
        yield {"stage": "generating", "message": "Generating code fixes with AI...", "progress": 55}
        changes = await self.generator.generate(interpretation, analysis)
        yield {"stage": "generated", "data": changes, "progress": 70,
               "message": f"Generated changes for {len(changes['modified_files'])} files"}

        # Stage 4
        yield {"stage": "creating_pr", "message": "Creating pull request...", "progress": 80}
        pr = await self.pr_manager.create_pr(interpretation, changes, repo_owner, repo_name)
        yield {"stage": "pr_created", "data": pr, "progress": 88,
               "message": f"PR #{pr['number']} created: {pr['title']}"}

        # Stage 5
        yield {"stage": "reviewing", "message": "Running automated code review...", "progress": 92}
        review = await self.reviewer.review(interpretation, changes, pr)
        yield {"stage": "reviewed", "data": review, "progress": 100,
               "message": f"Review complete: {review['verdict']}"}

        yield {
            "stage": "complete",
            "pipeline_id": self.pipeline_id,
            "message": "Pipeline completed successfully",
            "summary": {
                "interpretation": interpretation,
                "analysis": analysis,
                "code_changes": changes,
                "pull_request": pr,
                "review": review
            }
        }
