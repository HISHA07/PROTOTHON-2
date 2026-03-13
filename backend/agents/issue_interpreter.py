"""
Agent 1: Issue Interpreter
Parses the issue, classifies the task type, extracts keywords and affected modules.
Uses Claude claude-sonnet-4-20250514 or falls back to smart rule-based parsing.
"""

import re
import json
from typing import Optional
import anthropic


class IssueInterpreter:
    """
    Interprets a GitHub issue and extracts structured metadata:
    - Task type (bug_fix / feature_request / improvement / refactor)
    - Affected keywords and modules
    - Priority and complexity estimate
    - Relevant file hints
    """

    TASK_KEYWORDS = {
        "bug_fix": ["bug", "fix", "error", "crash", "broken", "exception", "fail", "wrong", "issue", "traceback"],
        "feature_request": ["add", "implement", "create", "new feature", "support", "enable", "allow"],
        "improvement": ["improve", "optimize", "enhance", "performance", "refactor", "clean", "simplify"],
        "security": ["security", "vulnerability", "injection", "xss", "csrf", "auth", "sanitize"],
    }

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
            except Exception:
                pass

    async def interpret(self, title: str, body: str) -> dict:
        """Main interpretation method. Uses Claude if available, else rule-based."""
        if self.client:
            return await self._interpret_with_ai(title, body)
        return self._interpret_rule_based(title, body)

    async def _interpret_with_ai(self, title: str, body: str) -> dict:
        """Use Claude to extract rich structured metadata from the issue."""
        prompt = f"""Analyze this GitHub issue and return a JSON object with these exact fields:
{{
  "task_type": "bug_fix|feature_request|improvement|security",
  "summary": "one sentence summary of what needs to be done",
  "affected_modules": ["list", "of", "module", "names"],
  "keywords": ["relevant", "technical", "keywords"],
  "priority": "low|medium|high|critical",
  "complexity": "simple|moderate|complex",
  "file_hints": ["possible", "filenames", "like", "login.py"],
  "root_cause": "what is causing the issue",
  "acceptance_criteria": ["what", "the", "fix", "should", "achieve"]
}}

Issue Title: {title}
Issue Body: {body}

Return ONLY valid JSON, no markdown."""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            text = message.content[0].text.strip()
            # Strip markdown fences if present
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            result = json.loads(text)
            result["interpreter"] = "claude-ai"
            return result
        except Exception as e:
            return self._interpret_rule_based(title, body)

    def _interpret_rule_based(self, title: str, body: str) -> dict:
        """Smart rule-based fallback when AI is not available."""
        combined = f"{title} {body}".lower()

        # Classify task type
        task_type = "improvement"
        for ttype, keywords in self.TASK_KEYWORDS.items():
            if any(kw in combined for kw in keywords):
                task_type = ttype
                break

        # Extract file hints from tracebacks and code blocks
        file_hints = re.findall(r'File ["\']?([a-zA-Z_/]+\.py)["\']?', body)
        file_hints += re.findall(r'`([a-zA-Z_/]+\.py)`', body)
        file_hints = list(set(file_hints))

        # Extract technical keywords
        keywords = []
        tech_terms = ["login", "auth", "password", "token", "database", "api", 
                      "validation", "error", "exception", "session", "cache",
                      "endpoint", "middleware", "model", "view", "controller"]
        keywords = [t for t in tech_terms if t in combined]

        # Guess affected modules from title/body
        modules = []
        module_hints = re.findall(r'\b([a-z_]+)\.(py|js|ts)\b', body)
        modules = [m[0] for m in module_hints]

        # Priority from language
        priority = "medium"
        if any(w in combined for w in ["critical", "urgent", "severe", "production"]):
            priority = "critical"
        elif any(w in combined for w in ["high", "important", "blocking"]):
            priority = "high"
        elif any(w in combined for w in ["low", "minor", "nice"]):
            priority = "low"

        return {
            "task_type": task_type,
            "summary": f"{task_type.replace('_', ' ').title()}: {title}",
            "affected_modules": modules or ["auth", "login"],
            "keywords": keywords or ["authentication", "validation"],
            "priority": priority,
            "complexity": "moderate",
            "file_hints": file_hints or self._guess_files(title, body),
            "root_cause": self._extract_root_cause(body),
            "acceptance_criteria": self._extract_criteria(body),
            "interpreter": "rule-based"
        }

    def _guess_files(self, title: str, body: str) -> list:
        """Heuristically guess relevant filenames from issue content."""
        guesses = []
        combined = f"{title} {body}".lower()
        if "login" in combined or "auth" in combined:
            guesses += ["auth/login.py", "auth/validators.py"]
        if "password" in combined:
            guesses += ["auth/password.py"]
        if "api" in combined or "endpoint" in combined:
            guesses += ["api/routes.py", "api/handlers.py"]
        if "database" in combined or "model" in combined:
            guesses += ["models/user.py"]
        return guesses or ["app/main.py"]

    def _extract_root_cause(self, body: str) -> str:
        """Pull root cause from traceback or actual behavior section."""
        traceback = re.search(r'```.*?```', body, re.DOTALL)
        if traceback:
            lines = traceback.group(0).split('\n')
            for line in lines:
                if 'Error' in line or 'Exception' in line:
                    return line.strip()
        if 'Actual Behavior' in body:
            section = body.split('Actual Behavior')[1].split('\n\n')[0]
            return section.strip()[:200]
        return "Root cause identified from issue description"

    def _extract_criteria(self, body: str) -> list:
        """Extract expected behavior as acceptance criteria."""
        if 'Expected Behavior' in body:
            section = body.split('Expected Behavior')[1].split('\n\n')[0]
            lines = [l.strip() for l in section.strip().split('\n') if l.strip()]
            return lines[:5]
        return ["Issue is resolved", "No regression in existing functionality", "Tests pass"]
