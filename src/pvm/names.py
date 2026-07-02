"""Shared identifier rules for assembly and bytecode validation."""

from __future__ import annotations

import re

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Matches a comment line that begins an entrypoint directive (with or without a name).
ENTRYPOINT_MALFORMED = re.compile(
    r"^\s*(?:;|#|//)\s*entrypoint\b",
    re.IGNORECASE,
)

ENTRYPOINT_LINE = re.compile(
    r"^\s*(?:;|#|//)\s*entrypoint\s+(.+?)\s*$",
    re.IGNORECASE,
)


def is_valid_identifier(name: str) -> bool:
    return bool(name and IDENTIFIER.match(name))
