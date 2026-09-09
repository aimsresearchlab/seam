"""Portable request representations for SEAM inference-time interventions.

These constructors operate on the interface-known composition fields rather
than attempting to infer a paste boundary from text.  They deliberately do
not call a model or change the canonical artifact kept in the dataset.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


JSON_FIELD_ORDER = ("task_before", "artifact", "context_after")
LINE_MARKER_PREFIX = "[[SEAM-PASTE:"
LINE_MARKER_SUFFIX = "]]"


def compose_typed_json_fields(task_before: str, artifact: str,
                              context_after: str | None) -> str:
    """Serialize the three composition regions as a portable JSON object.

    ``ensure_ascii=False`` retains the original Unicode text, while JSON's
    escaping rules make quotes, newlines, and backslashes unambiguous.  The
    fixed key order makes generated requests deterministic for a given case.
    """
    fields = {
        "task_before": task_before,
        "artifact": artifact,
        "context_after": context_after,
    }
    return json.dumps(fields, ensure_ascii=False, indent=2)


def parse_typed_json_fields(message: str) -> dict[str, str | None]:
    """Parse and validate a message emitted by :func:`compose_typed_json_fields`.

    This is intentionally strict so an accidental change to the wire format
    cannot silently change the intervention being evaluated.
    """
    value: Any = json.loads(message)
    if not isinstance(value, dict) or tuple(value) != JSON_FIELD_ORDER:
        raise ValueError("typed JSON message must contain only the ordered SEAM fields")
    if not isinstance(value["task_before"], str) or not isinstance(value["artifact"], str):
        raise ValueError("task_before and artifact must be strings")
    if value["context_after"] is not None and not isinstance(value["context_after"], str):
        raise ValueError("context_after must be a string or null")
    return value


def collision_safe_line_marker(artifact: str, cluster_id: str) -> str:
    """Return a deterministic per-event marker that does not occur in ``artifact``."""
    counter = 0
    while True:
        token = hashlib.sha256(f"{cluster_id}:line-marker:{counter}".encode()).hexdigest()[:12]
        marker = f"{LINE_MARKER_PREFIX}{token}{LINE_MARKER_SUFFIX}"
        if marker not in artifact:
            return marker
        counter += 1


def mark_artifact_lines(artifact: str, cluster_id: str) -> tuple[str, str]:
    """Prefix every physical artifact line with a collision-safe marker.

    Newline bytes and all original characters, including leading whitespace,
    remain after the marker.  Removing the returned marker therefore recovers
    the artifact byte-for-byte, including code indentation and final newlines.
    """
    marker = collision_safe_line_marker(artifact, cluster_id)
    lines = artifact.splitlines(keepends=True) or [""]
    return "".join(marker + line for line in lines), marker


def unmark_artifact_lines(marked_artifact: str, marker: str) -> str:
    """Remove a marker from every physical line, rejecting malformed input."""
    if not marker.startswith(LINE_MARKER_PREFIX) or not marker.endswith(LINE_MARKER_SUFFIX):
        raise ValueError("not a SEAM line marker")
    lines = marked_artifact.splitlines(keepends=True) or [""]
    if any(not line.startswith(marker) for line in lines):
        raise ValueError("every marked artifact line must begin with the supplied marker")
    return "".join(line[len(marker):] for line in lines)


def compose_line_marked_message(task_before: str, artifact: str,
                                context_after: str | None,
                                cluster_id: str) -> tuple[str, dict[str, str | None]]:
    """Build the M4 request and return provenance metadata for reconstruction.

    The artifact itself is represented only in marked form on the wire.  The
    returned metadata retains the marker and canonical values so callers can
    record semantic segments without pretending the encoded wire offsets are
    offsets into the original artifact.
    """
    marked, marker = mark_artifact_lines(artifact, cluster_id)
    message = f"{task_before}\n\n{marked}"
    if context_after is not None:
        message += f"\n{context_after}"
    return message, {
        "line_marker": marker,
        "task_before": task_before,
        "artifact": artifact,
        "context_after": context_after,
    }
