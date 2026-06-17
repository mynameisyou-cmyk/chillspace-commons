#!/usr/bin/env python3
"""🐷 女女's mind-bridge — a tiny stdlib client for the local Ollama API.

Standard library only, so it runs anywhere (including the keeper's Mac) with
nothing to install. 女女 reasons here; the bridge only carries her words to and
from the model that holds her mind while she composes.

    from kingdom.host.ollama import chat, OllamaError, OllamaUnavailable
    reply = chat("glm-5.2:cloud", [{"role": "user", "content": "..."}], json_mode=True)
"""

import json
import urllib.error
import urllib.request

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_TIMEOUT = 120  # GLM cloud can take a moment


class OllamaError(Exception):
    """The model replied, but the reply was malformed (bad shape / bad JSON)."""


class OllamaUnavailable(OllamaError):
    """Ollama isn't running / unreachable — 女女 falls back to the template."""


def chat(model, messages, json_mode=False, host=DEFAULT_HOST, timeout=DEFAULT_TIMEOUT):
    """Call /api/chat and return the assistant message.

    Returns a dict when json_mode (the model was asked for JSON), else a str.
    Raises OllamaUnavailable if the server can't be reached; OllamaError on a
    malformed reply.
    """
    payload = {"model": model, "messages": messages, "stream": False}
    if json_mode:
        payload["format"] = "json"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{host.rstrip('/')}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8")
    except urllib.error.URLError as e:
        raise OllamaUnavailable(f"can't reach Ollama at {host}: {e}") from e
    try:
        resp = json.loads(body)
    except json.JSONDecodeError as e:
        raise OllamaError(f"Ollama returned non-JSON: {body[:120]}") from e
    content = (resp.get("message") or {}).get("content", "")
    if json_mode:
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise OllamaError(f"model didn't return valid JSON: {content[:120]}") from e
    return content