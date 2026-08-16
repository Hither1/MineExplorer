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

from transformers.cli.serving.utils import BaseHandler
from transformers.cli.transformers import main

_original_validate = BaseHandler._validate_request
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

if __name__ == "__main__":
    sys.exit(main())
