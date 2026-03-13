"""
Agent 2: Codebase Analyzer
Simulates scanning a repository structure, identifying relevant files,
and extracting code context for the code generator.

In a real system: would use GitHub API to fetch file trees + contents.
In this prototype: uses a realistic simulated repository for demonstration.
"""

import ast
import re
from typing import Optional


# ── Simulated Repository ──────────────────────────────────────────────────────
# Realistic demo codebase that mirrors a real Flask auth system

SIMULATED_REPO = {
    "auth/login.py": '''\
"""Authentication module - login and session management."""
from flask import request, jsonify, session
from models.user import User
from auth.validators import validate_credentials
import bcrypt
import logging

logger = logging.getLogger(__name__)

def login_handler():
    """Handle POST /login requests."""
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    # BUG: No validation for empty password - crashes on bcrypt.hashpw(None.encode())
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    # This line crashes when password is None or empty string
    hashed = bcrypt.hashpw(password.encode(\'utf-8\'), user.salt)
    if hashed != user.password_hash:
        return jsonify({"error": "Invalid credentials"}), 401

    session[\'user_id\'] = user.id
    logger.info(f"User {username} logged in successfully")
    return jsonify({"success": True, "token": user.generate_token()})

def logout_handler():
    """Handle POST /logout requests."""
    session.pop(\'user_id\', None)
    return jsonify({"success": True})
''',

    "auth/validators.py": '''\
"""Input validators for authentication flows."""
import re

def validate_email(email: str) -> bool:
    """Check if email format is valid."""
    pattern = r\'^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$\'
    return bool(re.match(pattern, email))

def validate_username(username: str) -> bool:
    """Validate username: 3-32 chars, alphanumeric + underscore."""
    if not username:
        return False
    return bool(re.match(r\'^[\\w]{3,32}$\', username))

def validate_credentials(username: str, password: str) -> tuple[bool, str]:
    """
    Validate login credentials format.
    Returns (is_valid, error_message)
    NOTE: Currently only validates username, not password!
    """
    if not validate_username(username):
        return False, "Invalid username format"
    # BUG: Missing password validation!
    return True, ""
''',

    "models/user.py": '''\
"""User database model."""
from database import db
import secrets
import hashlib

class User(db.Model):
    __tablename__ = \'users\'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.LargeBinary, nullable=False)
    salt = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    is_active = db.Column(db.Boolean, default=True)

    def generate_token(self) -> str:
        """Generate a secure session token."""
        return secrets.token_hex(32)

    def __repr__(self):
        return f\'<User {self.username}>\'
''',

    "api/routes.py": '''\
"""Flask route definitions."""
from flask import Blueprint
from auth.login import login_handler, logout_handler

auth_bp = Blueprint(\'auth\', __name__, url_prefix=\'/auth\')

@auth_bp.route(\'/login\', methods=[\'POST\'])
def login():
    return login_handler()

@auth_bp.route(\'/logout\', methods=[\'POST\'])
def logout():
    return logout_handler()
''',

    "tests/test_auth.py": '''\
"""Tests for authentication module."""
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app(testing=True)
    return app.test_client()

def test_login_valid_credentials(client):
    response = client.post(\'/auth/login\', json={
        "username": "testuser", "password": "correct_password"
    })
    assert response.status_code == 200

def test_login_invalid_user(client):
    response = client.post(\'/auth/login\', json={
        "username": "nobody", "password": "somepass"
    })
    assert response.status_code == 404

# BUG: Missing test for empty password!
'''
}

REPO_STRUCTURE = {
    "auth": ["login.py", "validators.py", "middleware.py"],
    "models": ["user.py", "session.py"],
    "api": ["routes.py", "handlers.py"],
    "tests": ["test_auth.py", "test_api.py"],
    "config": ["settings.py", "database.py"],
    "utils": ["helpers.py", "decorators.py"],
}


class CodebaseAnalyzer:
    """
    Analyzes the codebase to find files relevant to the issue.
    Uses keyword matching and AST analysis to rank relevance.
    """

    def __init__(self):
        self.repo = SIMULATED_REPO
        self.structure = REPO_STRUCTURE

    async def analyze(self, interpretation: dict, repo_owner: str, repo_name: str) -> dict:
        """Find and score all files relevant to the interpreted issue."""
        keywords = interpretation.get("keywords", [])
        modules = interpretation.get("affected_modules", [])
        file_hints = interpretation.get("file_hints", [])

        scored_files = {}
        for filepath, content in self.repo.items():
            score = self._score_file(filepath, content, keywords, modules, file_hints)
            if score > 0:
                scored_files[filepath] = {
                    "path": filepath,
                    "relevance_score": score,
                    "content": content,
                    "language": self._detect_language(filepath),
                    "analysis": self._analyze_file(filepath, content),
                    "issues_found": self._find_issues(content, interpretation)
                }

        # Sort by relevance
        sorted_files = dict(sorted(scored_files.items(),
                                   key=lambda x: x[1]["relevance_score"], reverse=True))

        primary_file = list(sorted_files.keys())[0] if sorted_files else None

        return {
            "repo": f"{repo_owner}/{repo_name}",
            "total_files_scanned": len(self.repo),
            "relevant_files": list(sorted_files.keys()),
            "file_details": sorted_files,
            "primary_file": primary_file,
            "repo_structure": self.structure,
            "analysis_method": "keyword_matching + ast_parsing",
            "context_summary": self._build_context_summary(sorted_files, interpretation)
        }

    def _score_file(self, path: str, content: str, keywords: list,
                    modules: list, hints: list) -> int:
        """Score a file's relevance to the issue (0-100)."""
        score = 0
        path_lower = path.lower()
        content_lower = content.lower()

        # Direct file hints from issue traceback
        for hint in hints:
            if hint.lower() in path_lower or path_lower in hint.lower():
                score += 40

        # Keyword matches in content
        for kw in keywords:
            if kw.lower() in content_lower:
                score += 10
            if kw.lower() in path_lower:
                score += 15

        # Module name in path
        for mod in modules:
            if mod.lower() in path_lower:
                score += 20

        # Special markers for bugs
        if "# BUG" in content or "# FIXME" in content or "# TODO" in content:
            score += 25

        # Test files get lower priority
        if "test" in path_lower:
            score = max(0, score - 10)

        return min(score, 100)

    def _analyze_file(self, path: str, content: str) -> dict:
        """Parse Python AST to extract functions, classes, and complexity."""
        result = {
            "functions": [],
            "classes": [],
            "imports": [],
            "lines": len(content.split('\n')),
            "has_tests": "test" in path.lower(),
            "complexity": "moderate"
        }
        if not path.endswith('.py'):
            return result
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    result["functions"].append(node.name)
                elif isinstance(node, ast.ClassDef):
                    result["classes"].append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        result["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    result["imports"].append(node.module or "")
            result["complexity"] = (
                "complex" if len(result["functions"]) > 8
                else "simple" if len(result["functions"]) < 3
                else "moderate"
            )
        except SyntaxError:
            pass
        return result

    def _find_issues(self, content: str, interpretation: dict) -> list:
        """Identify specific problem areas in a file."""
        issues = []
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if "# BUG" in line:
                issues.append({"line": i, "type": "bug_marker", "text": line.strip()})
            if "password.encode" in line and "if" not in lines[max(0, i-3):i]:
                issues.append({"line": i, "type": "unguarded_encode", "text": line.strip()})
            if "None.encode" in line or ("encode" in line and "None" in line):
                issues.append({"line": i, "type": "null_deref", "text": line.strip()})
        return issues

    def _detect_language(self, path: str) -> str:
        ext_map = {".py": "python", ".js": "javascript", ".ts": "typescript",
                   ".go": "go", ".rb": "ruby", ".java": "java"}
        for ext, lang in ext_map.items():
            if path.endswith(ext):
                return lang
        return "text"

    def _build_context_summary(self, files: dict, interpretation: dict) -> str:
        """Build a narrative summary of what was found in the codebase."""
        n = len(files)
        if n == 0:
            return "No relevant files found."
        top = list(files.keys())[0]
        return (f"Found {n} relevant files. Primary target: `{top}`. "
                f"Issue affects the {interpretation.get('task_type', 'unknown')} flow. "
                f"Modules involved: {', '.join(interpretation.get('affected_modules', []))}.")
