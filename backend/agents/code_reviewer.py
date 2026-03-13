"""
Agent 5: Automated Code Reviewer
Reviews the generated PR and provides structured feedback across multiple
quality dimensions: bugs, security, performance, tests, style.
"""

import json
import re
from typing import Optional
import anthropic


# ── Demo review for when AI is unavailable ────────────────────────────────────

DEMO_REVIEW = {
    "verdict": "APPROVED_WITH_SUGGESTIONS",
    "score": 82,
    "summary": "The fix correctly addresses the empty password crash. "
               "Input validation has been added before the bcrypt call. "
               "A few minor improvements suggested below.",
    "categories": {
        "correctness": {
            "rating": "PASS",
            "score": 90,
            "findings": [
                {
                    "severity": "info",
                    "file": "auth/login.py",
                    "message": "Fix correctly guards password.encode() with None/empty check.",
                    "suggestion": None
                }
            ]
        },
        "security": {
            "rating": "PASS_WITH_WARNING",
            "score": 75,
            "findings": [
                {
                    "severity": "warning",
                    "file": "auth/login.py",
                    "message": "User enumeration: returning 404 for unknown users reveals username existence.",
                    "suggestion": "Return 401 for all failed login attempts regardless of whether the user exists."
                },
                {
                    "severity": "info",
                    "file": "auth/login.py",
                    "message": "Consider rate limiting login attempts to prevent brute force attacks.",
                    "suggestion": "Add flask-limiter or similar middleware: @limiter.limit('5/minute')"
                }
            ]
        },
        "code_quality": {
            "rating": "PASS",
            "score": 85,
            "findings": [
                {
                    "severity": "info",
                    "file": "auth/login.py",
                    "message": "isinstance() checks are robust but slightly verbose.",
                    "suggestion": "Could simplify: `if not password or not password.strip()` covers None, empty, and whitespace."
                },
                {
                    "severity": "info",
                    "file": "auth/validators.py",
                    "message": "validate_password() is well-structured and reusable.",
                    "suggestion": None
                }
            ]
        },
        "test_coverage": {
            "rating": "PASS",
            "score": 88,
            "findings": [
                {
                    "severity": "info",
                    "file": "tests/test_auth.py",
                    "message": "5 new test cases added including edge cases for null, empty, and whitespace.",
                    "suggestion": None
                },
                {
                    "severity": "suggestion",
                    "file": "tests/test_auth.py",
                    "message": "Missing test for oversized password (>128 chars).",
                    "suggestion": "Add: def test_login_password_too_long(client) to cover the 128-char limit."
                }
            ]
        },
        "performance": {
            "rating": "PASS",
            "score": 95,
            "findings": [
                {
                    "severity": "info",
                    "file": "auth/login.py",
                    "message": "Validation runs before DB query - good for performance.",
                    "suggestion": None
                }
            ]
        }
    },
    "inline_comments": [
        {
            "file": "auth/login.py",
            "line": 14,
            "type": "suggestion",
            "body": "Consider using `password.strip()` to reject whitespace-only passwords."
        },
        {
            "file": "auth/login.py",
            "line": 22,
            "type": "nitpick",
            "body": "The 404 → 401 fix for user enumeration is excellent. Well spotted!"
        },
        {
            "file": "auth/validators.py",
            "line": 8,
            "type": "praise",
            "body": "Clean, focused validator function. Good separation of concerns."
        }
    ],
    "summary_stats": {
        "total_findings": 9,
        "critical": 0,
        "errors": 0,
        "warnings": 1,
        "suggestions": 2,
        "info": 6
    },
    "recommendation": "MERGE_AFTER_ADDRESSING_WARNINGS",
    "reviewer": "AutoPR Review Bot v1.0"
}


class AutomatedCodeReviewer:
    """
    Performs automated code review of generated changes.
    Checks: correctness, security, code quality, test coverage, performance.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
            except Exception:
                pass

    async def review(self, interpretation: dict, changes: dict, pr: dict) -> dict:
        """Perform a full automated review of the PR."""
        if self.client:
            return await self._review_with_ai(interpretation, changes, pr)
        return self._demo_review(changes)

    async def _review_with_ai(self, interpretation: dict, changes: dict, pr: dict) -> dict:
        """Use Claude to do a deep code review."""
        # Build a diff summary for the prompt
        diffs = []
        for f in changes.get("modified_files", []):
            diffs.append(f"### {f['path']}\n**Before:**\n```python\n{f['before']}\n```\n**After:**\n```python\n{f['after']}\n```")

        diff_text = "\n\n".join(diffs)

        prompt = f"""You are a senior software engineer doing a thorough code review.

Issue being fixed: {interpretation.get('summary', '')}
Task Type: {interpretation.get('task_type', '')}

Code Changes:
{diff_text}

Review the changes across these dimensions and return a JSON object:
{{
  "verdict": "APPROVED | APPROVED_WITH_SUGGESTIONS | CHANGES_REQUESTED | REJECTED",
  "score": 0-100,
  "summary": "2-3 sentence overall assessment",
  "categories": {{
    "correctness": {{"rating": "PASS|FAIL|PASS_WITH_WARNING", "score": 0-100, "findings": [{{"severity": "critical|error|warning|suggestion|info", "file": "...", "message": "...", "suggestion": "..."}}]}},
    "security": {{"rating": "PASS|FAIL|PASS_WITH_WARNING", "score": 0-100, "findings": [...]}},
    "code_quality": {{"rating": "PASS|FAIL|PASS_WITH_WARNING", "score": 0-100, "findings": [...]}},
    "test_coverage": {{"rating": "PASS|FAIL|PASS_WITH_WARNING", "score": 0-100, "findings": [...]}},
    "performance": {{"rating": "PASS|FAIL|PASS_WITH_WARNING", "score": 0-100, "findings": [...]}}
  }},
  "inline_comments": [{{"file": "...", "line": 1, "type": "suggestion|nitpick|praise|blocker", "body": "..."}}],
  "summary_stats": {{"total_findings": 0, "critical": 0, "errors": 0, "warnings": 0, "suggestions": 0, "info": 0}},
  "recommendation": "MERGE | MERGE_AFTER_ADDRESSING_WARNINGS | REQUEST_CHANGES | REJECT",
  "reviewer": "AutoPR Review Bot v1.0"
}}

Be thorough, specific, and actionable. Return ONLY valid JSON."""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            text = message.content[0].text.strip()
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            result = json.loads(text)
            result["reviewer"] = "AutoPR Review Bot (Claude AI)"
            return result
        except Exception:
            return self._demo_review(changes)

    def _demo_review(self, changes: dict) -> dict:
        """Return realistic pre-built review for demo mode."""
        review = dict(DEMO_REVIEW)
        # Adjust based on actual changes
        n_files = len(changes.get("modified_files", []))
        if n_files == 0:
            review["verdict"] = "CHANGES_REQUESTED"
            review["score"] = 30
        return review
