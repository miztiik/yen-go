"""Streaming HTTP client for llama.cpp (OpenAI-compatible API).

Uses stdlib http.client -- no openai SDK dependency. Handles:
- SSE streaming with reasoning_content + content separation
- Markdown fence stripping
- Empty content detection (thinking exhausted budget)
- ASCII-only validation on prompts
- Progress callbacks for live token counts

Token budget note:
  max_tokens is a SHARED budget for thinking (reasoning_content) + output (content).
  The server's n_ctx (context window) is the hard ceiling -- currently 32768.
  After subtracting ~500-700 tokens for system + user prompt, ~30K is the safe max
  for max_tokens. Setting it too low (e.g. 8192) causes complex puzzles to exhaust
  the budget on thinking alone, producing empty content with 0 output tokens.
  More thinking tokens generally = better quality output.
"""
from __future__ import annotations

import http.client
import json
import logging
import time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ASCII-only check: llama.cpp JSON parser rejects multi-byte UTF-8
_NON_ASCII_RE_MSG = "Prompt contains non-ASCII characters which may cause llama.cpp parse errors"


@dataclass
class LLMResponse:
    """Result of a single LLM call."""
    content: str           # Final JSON output (after fence stripping)
    reasoning: str         # Thinking tokens (tail 500 chars for debug)
    think_tokens: int
    content_tokens: int
    elapsed_s: float
    finish_reason: str     # "done", "length", "error"
    error: str = ""        # Error message if finish_reason == "error"


def _validate_ascii(text: str, label: str) -> None:
    """Warn if text contains non-ASCII characters."""
    for i, ch in enumerate(text):
        if ord(ch) > 127:
            logger.warning(
                "%s: non-ASCII char U+%04X at position %d in %s",
                _NON_ASCII_RE_MSG, ord(ch), i, label,
            )
            return


def _strip_markdown_fences(content: str) -> str:
    """Strip ```json ... ``` or ``` ... ``` fences from LLM output."""
    if "```json" in content:
        return content.split("```json")[-1].split("```")[0].strip()
    if "```" in content:
        parts = content.split("```")
        if len(parts) >= 3:
            return parts[1].strip()
    return content.strip()


def call_llm(
    system_prompt: str,
    user_prompt: str,
    endpoint: str = "http://127.0.0.1:8080",
    model: str = "gemma-4-26B-A4B-it-Q8_0.gguf",
    max_tokens: int = 64000,
    temperature: float = 0.5,
    timeout_s: int = 600,
    progress_cb: Callable[[int, int, float], None] | None = None,
) -> LLMResponse:
    """Call the LLM endpoint with streaming and return structured response.

    Args:
        system_prompt: System message (voice rules, format instructions).
        user_prompt: User message (puzzle description).
        endpoint: Base URL of the llama.cpp server.
        model: Model name for the API request.
        max_tokens: Maximum tokens to generate.
        temperature: Sampling temperature.
        timeout_s: HTTP timeout in seconds.
        progress_cb: Optional callback(think_tokens, content_tokens, elapsed_s)
            called every ~15 seconds during generation.

    Returns:
        LLMResponse with parsed content and metrics.
    """
    _validate_ascii(system_prompt, "system_prompt")
    _validate_ascii(user_prompt, "user_prompt")

    parsed = urlparse(endpoint)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8080

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    })

    try:
        conn = http.client.HTTPConnection(host, port, timeout=timeout_s)
        conn.request(
            "POST", "/v1/chat/completions",
            body=payload,
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
    except Exception as e:
        return LLMResponse(
            content="", reasoning="", think_tokens=0, content_tokens=0,
            elapsed_s=0.0, finish_reason="error", error=str(e),
        )

    if response.status != 200:
        err = response.read().decode("utf-8", errors="replace")[:500]
        conn.close()
        return LLMResponse(
            content="", reasoning="", think_tokens=0, content_tokens=0,
            elapsed_s=0.0, finish_reason="error",
            error=f"HTTP {response.status}: {err}",
        )

    # Parse SSE stream
    r_tok = 0
    c_tok = 0
    r_text: list[str] = []
    c_text: list[str] = []
    start = time.time()
    last_report = start
    finish_reason: str | None = None
    buf = ""

    for chunk in response:
        buf += chunk.decode("utf-8", errors="replace")
        while "\n\n" in buf:
            ev, buf = buf.split("\n\n", 1)
            for ln in ev.strip().split("\n"):
                if not ln.startswith("data: "):
                    continue
                ds = ln[6:]
                if ds.strip() == "[DONE]":
                    finish_reason = finish_reason or "done"
                    continue
                try:
                    d = json.loads(ds)
                except json.JSONDecodeError:
                    continue
                ch = d.get("choices", [{}])[0]
                delta = ch.get("delta", {})
                if ch.get("finish_reason"):
                    finish_reason = ch["finish_reason"]
                if delta.get("reasoning_content"):
                    r_tok += 1
                    r_text.append(delta["reasoning_content"])
                if delta.get("content"):
                    c_tok += 1
                    c_text.append(delta["content"])

            now = time.time()
            if progress_cb and now - last_report > 15:
                progress_cb(r_tok, c_tok, now - start)
                last_report = now

    conn.close()
    elapsed = time.time() - start
    content = "".join(c_text)
    content = _strip_markdown_fences(content)
    reasoning = "".join(r_text)

    # Detect empty content (thinking exhausted the budget)
    if not content.strip() and r_tok > 0:
        logger.warning(
            "Empty content after %d thinking tokens (%.0fs) -- "
            "budget likely exhausted. Consider increasing max_tokens.",
            r_tok, elapsed,
        )
        finish_reason = "empty_content"

    return LLMResponse(
        content=content,
        reasoning=reasoning,  # full reasoning for I/O logging
        think_tokens=r_tok,
        content_tokens=c_tok,
        elapsed_s=elapsed,
        finish_reason=finish_reason or "unknown",
    )


def check_server(endpoint: str = "http://127.0.0.1:8080") -> dict | None:
    """Check if the LLM server is reachable. Returns model info or None."""
    parsed = urlparse(endpoint)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8080
    try:
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/v1/models")
        resp = conn.getresponse()
        if resp.status == 200:
            data = json.loads(resp.read().decode("utf-8"))
            conn.close()
            return data
        conn.close()
    except Exception:
        pass
    return None
