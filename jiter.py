"""Pure-Python fallback for environments that block jiter's native extension.

The OpenAI SDK imports :func:`from_json` for streaming response parsing even
when an application only makes non-streaming requests.  Some Windows
Application Control policies block the bundled ``jiter.pyd`` file, preventing
the SDK from importing at all.  This small compatibility module keeps normal
JSON parsing available without loading that native binary.
"""

from __future__ import annotations

import json
from typing import Any


def from_json(data: bytes | bytearray | str, *, partial_mode: bool = False) -> Any:
    """Decode complete JSON using the standard library.

    ``partial_mode`` is accepted for API compatibility.  The evaluator uses
    non-streaming requests, so it never relies on jiter's incremental parser.
    """
    del partial_mode
    return json.loads(data)
