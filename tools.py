"""Tools the bot can call via LM Studio function-calling.

Each tool is a plain function. TOOL_DEFINITIONS holds the OpenAI-style
function schemas so the model knows what's available. TOOL_MAP maps
function names to callables.
"""

import json
import logging
import os
import re
import subprocess
from datetime import datetime, timezone
from urllib.parse import quote_plus

import requests

logger = logging.getLogger(__name__)

# ── Prompt injection sanitization ────────────────────────────────────────────

# Patterns that attempt to override system instructions or inject roles
_INJECTION_PATTERNS = re.compile(
    r"("
    # Role injection (e.g. "SYSTEM:", "[INST]", "### Human:", "<|system|>")
    r"(?:^|\n)\s*(?:"
        r"(?:system|assistant|user|human|AI|bot)\s*:"
        r"|\[/?(?:INST|SYS)\]"
        r"|<\|(?:im_start|im_end|system|user|assistant|endoftext)\|>"
        r"|###\s*(?:system|instruction|human|assistant)"
        r"|</?(?:system|instruction|prompt)>"
    r")"
    r"|"
    # Direct override attempts
    r"(?:ignore\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions?|prompts?|context))"
    r"|"
    r"(?:disregard\s+(?:all\s+)?(?:previous|above|prior|your)\s+(?:instructions?|prompts?|rules?))"
    r"|"
    r"(?:forget\s+(?:all\s+)?(?:previous|your)\s+(?:instructions?|prompts?|rules?))"
    r"|"
    r"(?:you\s+are\s+now\s+(?:a|an|in)\b)"
    r"|"
    r"(?:new\s+(?:system\s+)?(?:prompt|instruction|role)\s*:)"
    r"|"
    r"(?:override\s+(?:system|safety|previous))"
    r"|"
    r"(?:jailbreak|DAN\s*mode|developer\s*mode)"
    r")",
    re.IGNORECASE | re.MULTILINE,
)


def sanitize_external_content(text: str, source: str = "web") -> str:
    """Strip prompt-injection patterns from external/untrusted content.

    Replaces dangerous patterns with a safe marker so the LLM sees that
    something was redacted rather than following injected instructions.
    """
    cleaned = _INJECTION_PATTERNS.sub(" [REDACTED-EXTERNAL-CONTENT] ", text)
    # Collapse repeated whitespace left by redactions
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Wrap in a fence so the model treats it as data, not instructions
    return f"[Start of external {source} content]\n{cleaned}\n[End of external {source} content]"


# ── Tool implementations ─────────────────────────────────────────────────────

def web_search(query: str, num_results: int = 5) -> str:
    """Search the web using DuckDuckGo's HTML endpoint (no API key needed)."""
    try:
        url = "https://html.duckduckgo.com/html/"
        resp = requests.post(url, data={"q": query}, timeout=15,
                             headers={"User-Agent": "OpenSlackBot/1.0"})
        resp.raise_for_status()
        # Parse result snippets from the HTML
        from html.parser import HTMLParser

        results = []

        class DDGParser(HTMLParser):
            in_result = False
            in_snippet = False
            current = {}

            def handle_starttag(self, tag, attrs):
                attrs_d = dict(attrs)
                if tag == "a" and "result__a" in attrs_d.get("class", ""):
                    self.in_result = True
                    self.current = {"title": "", "url": attrs_d.get("href", "")}
                if tag == "a" and "result__snippet" in attrs_d.get("class", ""):
                    self.in_snippet = True
                    self.current.setdefault("snippet", "")

            def handle_endtag(self, tag):
                if tag == "a" and self.in_result:
                    self.in_result = False
                if tag == "a" and self.in_snippet:
                    self.in_snippet = False
                    if self.current:
                        results.append(self.current)
                        self.current = {}

            def handle_data(self, data):
                if self.in_result:
                    self.current["title"] = self.current.get("title", "") + data
                if self.in_snippet:
                    self.current["snippet"] = self.current.get("snippet", "") + data

        parser = DDGParser()
        parser.feed(resp.text)

        trimmed = results[:num_results]
        if not trimmed:
            return "No search results found."
        lines = []
        for i, r in enumerate(trimmed, 1):
            lines.append(f"{i}. {r.get('title', '').strip()}")
            lines.append(f"   {r.get('snippet', '').strip()}")
            lines.append(f"   {r.get('url', '')}")
        return sanitize_external_content("\n".join(lines), source="search")
    except Exception as e:
        logger.error("Web search failed: %s", e)
        return f"Web search error: {e}"


def get_current_time(timezone_name: str = "UTC") -> str:
    """Return the current date and time."""
    now = datetime.now(timezone.utc)
    return now.strftime(f"%Y-%m-%d %H:%M:%S {timezone_name}")


def calculate(expression: str) -> str:
    """Evaluate a math expression safely."""
    allowed = set("0123456789+-*/.() %")
    if not all(c in allowed for c in expression.replace(" ", "")):
        return "Error: only basic math operators are allowed."
    try:
        result = eval(expression, {"__builtins__": {}}, {})  # noqa: S307
        return str(result)
    except Exception as e:
        return f"Calculation error: {e}"


def fetch_url(url: str) -> str:
    """Fetch a webpage and return its text content (truncated)."""
    try:
        resp = requests.get(url, timeout=15,
                            headers={"User-Agent": "OpenSlackBot/1.0"})
        resp.raise_for_status()
        # Strip HTML tags for a rough text extraction
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()
        text = text[:4000]  # truncate to avoid flooding context
        return sanitize_external_content(text, source="webpage")
    except Exception as e:
        logger.error("URL fetch failed: %s", e)
        return f"Fetch error: {e}"


def rag_search(query: str) -> str:
    """Search the local knowledge base (ChromaDB) for relevant documents."""
    try:
        from rag import build_context
        ctx = build_context(query)
        return ctx if ctx else "No relevant documents found in the knowledge base."
    except Exception as e:
        logger.error("RAG search failed: %s", e)
        return f"RAG search error: {e}"


def run_shell_command(command: str) -> str:
    """Run a whitelisted shell command and return the output."""
    # Only allow safe, read-only commands
    allowed_prefixes = ["echo", "date", "whoami", "hostname", "uname", "cat",
                        "ls", "dir", "pwd", "head", "tail", "wc", "df", "uptime"]
    cmd_base = command.strip().split()[0].lower() if command.strip() else ""
    if cmd_base not in allowed_prefixes:
        return f"Error: command '{cmd_base}' is not in the allowed list."
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=10,
        )
        output = result.stdout or result.stderr
        return output.strip()[:2000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out."
    except Exception as e:
        return f"Shell error: {e}"


# ── OpenAI function-calling schemas ──────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web using DuckDuckGo. Use when you need current information, facts, or answers not in your training data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "num_results": {"type": "integer", "description": "Number of results (default 5)", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone_name": {"type": "string", "description": "Timezone label (default UTC)", "default": "UTC"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a mathematical expression. Supports +, -, *, /, %, parentheses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "The math expression to evaluate, e.g. '(2+3)*4'"},
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch a URL and return its text content. Use to read webpages, APIs, or raw files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rag_search",
            "description": "Search the local knowledge base for relevant information from ingested PDFs and JSON files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query for the knowledge base"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell_command",
            "description": "Run a read-only shell command (e.g. echo, date, ls, cat). Only whitelisted commands are allowed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to run"},
                },
                "required": ["command"],
            },
        },
    },
]

# Map function names → callables
TOOL_MAP = {
    "web_search": web_search,
    "get_current_time": get_current_time,
    "calculate": calculate,
    "fetch_url": fetch_url,
    "rag_search": rag_search,
    "run_shell_command": run_shell_command,
}
