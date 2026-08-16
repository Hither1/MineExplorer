"""`transformers serve`, made tolerant of the extra fields the Codex CLI sends.

Codex posts `client_metadata` on every `/v1/responses` request. Transformers validates
the body against the OpenAI params TypedDict and rejects *any* unrecognised key with a
422, so the very first turn dies before the model is ever consulted:

    422 Unprocessable Entity: {"detail":"Unexpected fields in the request: {'client_metadata'}"}

Transformers already has an "ignore, don't reject" path (`_unused_fields`), so tolerance
is the maintainers' own intent for fields it does not implement — the list simply
predates this client. Rather than edit site-packages, drop unknown keys here and log
each one, so anything Codex adds in future shows up in the server log instead of
silently changing behaviour.

Usage is identical to the real CLI:

    python scripts/serve_qwen_for_codex.py serve <model> --host ... --port ...
"""

import sys

from transformers.cli.serving.response import ResponseHandler
from transformers.cli.serving.utils import BaseHandler
from transformers.cli.transformers import main

# Qwen3.5's chat template accepts only system/user/assistant/tool and raises
# `Unexpected message role.` on anything else. The Responses API uses `developer`
# where chat completions used `system`, and transformers passes item roles through
# verbatim, so a codex turn reaches Jinja with a role the template rejects and the
# request 500s. Map it to the equivalent the template does understand.
_ROLE_ALIASES = {"developer": "system"}

_original_validate = BaseHandler._validate_request
_original_normalize = ResponseHandler._normalize_input
_reported: set[str] = set()


def _validate_leniently(self, body: dict) -> None:
    valid = getattr(self._valid_params_class, "__mutable_keys__", None)
    if valid:
        for key in set(body) - set(valid):
            body.pop(key, None)
            if key not in _reported:
                _reported.add(key)
                print(f"[codex-shim] dropping unsupported request field: {key!r}", flush=True)
    return _original_validate(self, body)


BaseHandler._validate_request = _validate_leniently


def _as_text(content) -> str:
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if isinstance(block, dict):
            parts.append(block.get("text") or block.get("content") or "")
        elif isinstance(block, str):
            parts.append(block)
    return "\n".join(p for p in parts if p)


def _normalize_input_with_role_aliases(body: dict) -> list:
    messages = _original_normalize(body)

    for msg in messages:
        role = msg.get("role")
        if role in _ROLE_ALIASES:
            msg["role"] = _ROLE_ALIASES[role]
            if role not in _reported:
                _reported.add(role)
                print(f"[codex-shim] mapping message role {role!r} -> {msg['role']!r}", flush=True)

    # Codex supplies both `instructions` (which transformers prepends as system) and a
    # `developer` item, so aliasing alone leaves two system messages and the template
    # then raises `System message must be at the beginning.` Fold them into one leader.
    system_parts = [_as_text(m.get("content")) for m in messages if m.get("role") == "system"]
    rest = [m for m in messages if m.get("role") != "system"]
    if len(system_parts) > 1 and "merged-system" not in _reported:
        _reported.add("merged-system")
        print(f"[codex-shim] merging {len(system_parts)} system messages into one leader", flush=True)
    if system_parts:
        return [{"role": "system", "content": "\n\n".join(p for p in system_parts if p)}] + rest
    return rest


ResponseHandler._normalize_input = staticmethod(_normalize_input_with_role_aliases)

if __name__ == "__main__":
    sys.exit(main())
