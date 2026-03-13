"""
Agent 4: Pull Request Manager
Creates a pull request via GitHub API or simulates one for demo purposes.
In simulation mode: produces a realistic PR object matching GitHub's API schema.
"""

import uuid
import json
from datetime import datetime
from typing import Optional
import httpx


class PullRequestManager:
    """
    Manages pull request creation.
    - Real mode: uses GitHub REST API to create branches, commits, and PRs
    - Simulation mode: produces a realistic PR object for demonstration
    """

    GITHUB_API = "https://api.github.com"

    def __init__(self, github_token: Optional[str] = None, use_real_github: bool = False):
        self.token = github_token
        self.use_real_github = use_real_github and bool(github_token)
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        } if github_token else {}

    async def create_pr(self, interpretation: dict, changes: dict,
                        repo_owner: str, repo_name: str) -> dict:
        """Create or simulate a pull request."""
        if self.use_real_github:
            return await self._create_real_pr(interpretation, changes, repo_owner, repo_name)
        return self._simulate_pr(interpretation, changes, repo_owner, repo_name)

    async def _create_real_pr(self, interpretation: dict, changes: dict,
                               repo_owner: str, repo_name: str) -> dict:
        """Create an actual PR via GitHub API."""
        branch = changes.get("branch_name", f"autopr/fix-{uuid.uuid4().hex[:6]}")
        title = self._build_pr_title(interpretation)
        body = self._build_pr_body(interpretation, changes)

        async with httpx.AsyncClient() as client:
            # Get default branch SHA
            repo_resp = await client.get(
                f"{self.GITHUB_API}/repos/{repo_owner}/{repo_name}",
                headers=self.headers
            )
            default_branch = repo_resp.json().get("default_branch", "main")

            branch_resp = await client.get(
                f"{self.GITHUB_API}/repos/{repo_owner}/{repo_name}/git/ref/heads/{default_branch}",
                headers=self.headers
            )
            sha = branch_resp.json()["object"]["sha"]

            # Create branch
            await client.post(
                f"{self.GITHUB_API}/repos/{repo_owner}/{repo_name}/git/refs",
                headers=self.headers,
                json={"ref": f"refs/heads/{branch}", "sha": sha}
            )

            # Create PR
            pr_resp = await client.post(
                f"{self.GITHUB_API}/repos/{repo_owner}/{repo_name}/pulls",
                headers=self.headers,
                json={
                    "title": title,
                    "body": body,
                    "head": branch,
                    "base": default_branch,
                    "draft": False,
                }
            )
            pr_data = pr_resp.json()
            return self._format_pr_response(pr_data, changes, branch)

    def _simulate_pr(self, interpretation: dict, changes: dict,
                     repo_owner: str, repo_name: str) -> dict:
        """Produce a realistic simulated PR matching GitHub API schema."""
        pr_number = 247  # Realistic-looking PR number
        branch = changes.get("branch_name", "autopr/fix/login-validation")
        title = self._build_pr_title(interpretation)
        body = self._build_pr_body(interpretation, changes)
        now = datetime.utcnow().isoformat() + "Z"

        return {
            "number": pr_number,
            "title": title,
            "body": body,
            "state": "open",
            "draft": False,
            "url": f"https://github.com/{repo_owner}/{repo_name}/pull/{pr_number}",
            "html_url": f"https://github.com/{repo_owner}/{repo_name}/pull/{pr_number}",
            "branch": branch,
            "base_branch": "main",
            "repo": f"{repo_owner}/{repo_name}",
            "created_at": now,
            "labels": self._generate_labels(interpretation),
            "reviewers": ["@autopr-bot"],
            "modified_files": [f["path"] for f in changes.get("modified_files", [])],
            "stats": {
                "total_additions": sum(f["lines_added"] for f in changes.get("modified_files", [])),
                "total_deletions": sum(f["lines_removed"] for f in changes.get("modified_files", [])),
                "files_changed": len(changes.get("modified_files", [])),
            },
            "commit": {
                "sha": uuid.uuid4().hex[:40],
                "message": changes.get("commit_message", "fix: address issue"),
                "author": "autopr-bot",
            },
            "simulated": True,
            "diff_url": f"https://github.com/{repo_owner}/{repo_name}/pull/{pr_number}.diff",
        }

    def _build_pr_title(self, interpretation: dict) -> str:
        task = interpretation.get("task_type", "fix")
        summary = interpretation.get("summary", "Address issue")
        prefix_map = {
            "bug_fix": "fix",
            "feature_request": "feat",
            "improvement": "refactor",
            "security": "security"
        }
        prefix = prefix_map.get(task, "fix")
        # Remove task-type prefix if already in summary
        clean_summary = summary.replace(f"{task.replace('_', ' ').title()}: ", "")
        return f"{prefix}: {clean_summary[:60]}"

    def _build_pr_body(self, interpretation: dict, changes: dict) -> str:
        files = "\n".join(
            f"- `{f['path']}` (+{f['lines_added']}/-{f['lines_removed']})"
            for f in changes.get("modified_files", [])
        )
        criteria = "\n".join(
            f"- [x] {c}" for c in interpretation.get("acceptance_criteria", [])
        )
        explanations = "\n".join(
            f"**{f['path']}**: {f.get('explanation', '')}"
            for f in changes.get("modified_files", [])
        )

        return f"""## Summary
{interpretation.get('summary', 'Addresses the reported issue.')}

## Changes
{files}

## Root Cause
{interpretation.get('root_cause', 'See issue for details.')}

## What Changed
{explanations}

## Acceptance Criteria
{criteria}

---
*🤖 This PR was automatically generated by [AutoPR](https://github.com/autopr) based on issue analysis.*
*Priority: **{interpretation.get('priority', 'medium').upper()}** | Complexity: **{interpretation.get('complexity', 'moderate')}***
"""

    def _generate_labels(self, interpretation: dict) -> list:
        label_map = {
            "bug_fix": ["bug", "autopr"],
            "feature_request": ["enhancement", "autopr"],
            "improvement": ["refactor", "autopr"],
            "security": ["security", "critical", "autopr"],
        }
        return label_map.get(interpretation.get("task_type", "bug_fix"), ["autopr"])

    def _format_pr_response(self, pr_data: dict, changes: dict, branch: str) -> dict:
        """Format GitHub API response into our standard schema."""
        return {
            "number": pr_data.get("number"),
            "title": pr_data.get("title"),
            "body": pr_data.get("body"),
            "state": pr_data.get("state", "open"),
            "url": pr_data.get("html_url"),
            "html_url": pr_data.get("html_url"),
            "branch": branch,
            "modified_files": [f["path"] for f in changes.get("modified_files", [])],
            "simulated": False,
        }
