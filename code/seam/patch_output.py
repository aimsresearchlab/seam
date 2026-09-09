"""Strict, provenance-aware patch output for artifact editing.

The model-facing representation is a small JSON object::

    {"version": 1, "edits": [
        {"start": 4, "end": 7, "replacement": "new"}
    ]}

``start`` and ``end`` are half-open offsets into the original artifact,
measured in Python Unicode code points (the same indexing used by ``str``).
Edits are applied simultaneously, so their spans must not overlap. Adjacent
edits are valid. An insertion has ``start == end``.

This module intentionally accepts only the JSON object itself. Markdown
fences, prose, unknown fields, and trailing JSON are rejected so that a
caller can treat format failures as a failed patch rather than silently
editing the artifact.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping


class PatchError(ValueError):
    """Raised when a patch is malformed or cannot be applied safely."""


PATCH_OUTPUT_INSTRUCTION = """Return only one JSON object describing edits to the artifact.
Use this exact schema: {\"version\":1,\"edits\":[{\"start\":0,\"end\":0,\"replacement\":\"text\"}]}.
Offsets are half-open Unicode code-point positions in the original artifact.
Use an empty edits array when no edit is needed. Do not use Markdown fences,
prose, or fields other than version, edits, start, end, and replacement.
"""


def patch_output_instruction() -> str:
    """Return the model-facing instruction for the strict patch format."""
    return PATCH_OUTPUT_INSTRUCTION


@dataclass(frozen=True)
class Edit:
    """One half-open replacement span in the original source string."""

    start: int
    end: int
    replacement: str


@dataclass(frozen=True)
class Patch:
    """A validated versioned patch."""

    version: int
    edits: tuple[Edit, ...]

    def validate(self, source: str) -> None:
        """Validate this patch against ``source`` without changing it."""
        if not isinstance(source, str):
            raise PatchError("source must be a string")
        if self.version != 1:
            raise PatchError(f"unsupported patch version: {self.version}")

        previous: Edit | None = None
        for edit in sorted(self.edits, key=lambda item: (item.start, item.end)):
            if (isinstance(edit.start, bool) or not isinstance(edit.start, int)
                    or isinstance(edit.end, bool) or not isinstance(edit.end, int)):
                raise PatchError("edit offsets must be integers")
            if not isinstance(edit.replacement, str):
                raise PatchError("edit replacement must be a string")
            if edit.start < 0 or edit.end < edit.start or edit.end > len(source):
                raise PatchError(
                    f"edit span [{edit.start}, {edit.end}) is outside source "
                    f"of length {len(source)}"
                )
            if previous is not None and edit.start < previous.end:
                raise PatchError(
                    f"overlapping edit spans [{previous.start}, {previous.end}) "
                    f"and [{edit.start}, {edit.end})"
                )
            previous = edit

    def apply(self, source: str) -> str:
        """Return ``source`` after applying all edits simultaneously."""
        self.validate(source)
        pieces: list[str] = []
        cursor = 0
        for edit in sorted(self.edits, key=lambda item: (item.start, item.end)):
            pieces.append(source[cursor:edit.start])
            pieces.append(edit.replacement)
            cursor = edit.end
        pieces.append(source[cursor:])
        return "".join(pieces)


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], where: str) -> None:
    unknown = set(value) - expected
    missing = expected - set(value)
    if unknown:
        raise PatchError(f"{where} has unknown field(s): {sorted(unknown)!r}")
    if missing:
        raise PatchError(f"{where} is missing field(s): {sorted(missing)!r}")


def _require_int(value: Any, where: str) -> int:
    # bool is a subclass of int, but is never a valid offset or version.
    if isinstance(value, bool) or not isinstance(value, int):
        raise PatchError(f"{where} must be an integer")
    return value


def parse_patch(payload: str | Mapping[str, Any]) -> Patch:
    """Parse and structurally validate a model-produced patch.

    The source-dependent span and overlap checks happen in ``Patch.validate``
    or ``Patch.apply`` because the source is not part of the patch payload.
    """
    if isinstance(payload, str):
        try:
            value = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise PatchError(f"invalid JSON: {exc.msg}") from exc
    elif isinstance(payload, Mapping):
        value = payload
    else:
        raise PatchError("patch payload must be a JSON string or object")

    if not isinstance(value, Mapping):
        raise PatchError("patch root must be a JSON object")
    _require_exact_keys(value, {"version", "edits"}, "patch")
    version = _require_int(value["version"], "patch.version")
    if version != 1:
        raise PatchError(f"unsupported patch version: {version}")

    raw_edits = value["edits"]
    if not isinstance(raw_edits, list):
        raise PatchError("patch.edits must be a JSON array")

    edits: list[Edit] = []
    for index, raw_edit in enumerate(raw_edits):
        where = f"patch.edits[{index}]"
        if not isinstance(raw_edit, Mapping):
            raise PatchError(f"{where} must be a JSON object")
        _require_exact_keys(raw_edit, {"start", "end", "replacement"}, where)
        replacement = raw_edit["replacement"]
        if not isinstance(replacement, str):
            raise PatchError(f"{where}.replacement must be a string")
        edits.append(
            Edit(
                start=_require_int(raw_edit["start"], f"{where}.start"),
                end=_require_int(raw_edit["end"], f"{where}.end"),
                replacement=replacement,
            )
        )

    return Patch(version=version, edits=tuple(edits))


def apply_patch(source: str, payload: str | Mapping[str, Any]) -> str:
    """Parse and safely apply a model-produced patch to ``source``."""
    return parse_patch(payload).apply(source)


def patch_to_json(patch: Patch) -> str:
    """Serialize a patch in canonical compact JSON for prompts or traces."""
    if not isinstance(patch, Patch):
        raise PatchError("patch_to_json expects a Patch")
    value = {
        "version": patch.version,
        "edits": [
            {"start": edit.start, "end": edit.end, "replacement": edit.replacement}
            for edit in patch.edits
        ],
    }
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
