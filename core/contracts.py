"""
core/contracts.py — Structured runtime contracts derived from agent output.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    status: str
    summary: str
    raw_output: str
    blocker_reason: str = ""
    files_written: list[str] = field(default_factory=list)
    tests_run: list[str] = field(default_factory=list)
    followups: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if str(value).strip():
        return [str(value)]
    return []


def _extract_result_payload(raw_output: str) -> dict[str, Any] | None:
    for line in reversed(raw_output.splitlines()):
        stripped = line.strip()
        if stripped.upper().startswith("RESULT_JSON:"):
            payload = stripped.split("RESULT_JSON:", 1)[1].strip()
            if not payload:
                raise ValueError("RESULT_JSON marker is present but empty")
            return json.loads(payload)

    # Fallback: support RESULT_JSON as a markdown section with a fenced JSON block
    return _extract_result_payload_from_markdown(raw_output)


def _extract_result_payload_from_markdown(raw_output: str) -> dict[str, Any] | None:
    lines = raw_output.splitlines()
    for idx, line in enumerate(lines):
        if "RESULT_JSON" in line.upper():
            # Skip marker line itself and blank lines
            j = idx + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j >= len(lines):
                continue

            next_line = lines[j].strip()
            if next_line.startswith("```"):
                j += 1
                block_lines = []
                while j < len(lines) and not lines[j].strip().startswith("```"):
                    block_lines.append(lines[j])
                    j += 1
                payload_text = "\n".join(block_lines).strip()
                if payload_text:
                    return json.loads(payload_text)
            elif next_line.startswith("{"):
                payload_text = _collect_json_block(lines[j:])
                if payload_text:
                    return json.loads(payload_text)
    return None


def _collect_json_block(lines: list[str]) -> str:
    buffer: list[str] = []
    depth = 0
    in_string = False
    escape = False
    for line in lines:
        buffer.append(line)
        for ch in line:
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
        if depth == 0 and buffer:
            break
    return "\n".join(buffer).strip() if depth == 0 else ""


def parse_agent_output(output: str, task_type: str | None = None) -> AgentResult:
    """Parse the terminal task marker from an agent response."""
    raw_output = output.strip()
    if not raw_output:
        return AgentResult(
            status="failed",
            summary="Agent returned empty output",
            raw_output=raw_output,
        )

    try:
        payload = _extract_result_payload(raw_output)
    except ValueError as exc:
        return AgentResult(
            status="failed",
            summary=str(exc),
            raw_output=raw_output,
        )
    except json.JSONDecodeError as exc:
        return AgentResult(
            status="failed",
            summary=f"Invalid RESULT_JSON payload: {exc.msg}",
            raw_output=raw_output,
        )

    for line in reversed(raw_output.splitlines()):
        stripped = line.strip()
        if stripped == "TASK COMPLETE" or stripped.startswith("TASK COMPLETE:"):
            summary = stripped.split(":", 1)[1].strip() if ":" in stripped else "Task complete"
            return AgentResult(
                status="complete",
                summary=str(payload.get("summary", summary)) if payload else summary,
                raw_output=raw_output,
                files_written=_normalize_string_list(payload.get("files_written")) if payload else [],
                tests_run=_normalize_string_list(payload.get("tests_run")) if payload else [],
                followups=_normalize_string_list(payload.get("followups")) if payload else [],
                payload=payload or {},
            )
        if stripped == "TASK BLOCKED" or stripped.startswith("TASK BLOCKED:"):
            reason = stripped.split(":", 1)[1].strip() if ":" in stripped else "Task blocked"
            return AgentResult(
                status="blocked",
                summary=str(payload.get("summary", reason)) if payload else reason,
                blocker_reason=str(payload.get("blocker_reason", reason)) if payload else reason,
                raw_output=raw_output,
                files_written=_normalize_string_list(payload.get("files_written")) if payload else [],
                tests_run=_normalize_string_list(payload.get("tests_run")) if payload else [],
                followups=_normalize_string_list(payload.get("followups")) if payload else [],
                payload=payload or {},
            )
        if stripped == "TASK FAILED" or stripped.startswith("TASK FAILED:"):
            reason = stripped.split(":", 1)[1].strip() if ":" in stripped else "Task failed"
            return AgentResult(
                status="failed",
                summary=str(payload.get("summary", reason)) if payload else reason,
                raw_output=raw_output,
                files_written=_normalize_string_list(payload.get("files_written")) if payload else [],
                tests_run=_normalize_string_list(payload.get("tests_run")) if payload else [],
                followups=_normalize_string_list(payload.get("followups")) if payload else [],
                payload=payload or {},
            )

    if payload and task_type == "plan":
        if isinstance(payload, dict) and "plan_markdown" in payload and "tasks_board" in payload:
            return AgentResult(
                status="complete",
                summary=str(payload.get("summary", "Planning complete")),
                raw_output=raw_output,
                files_written=_normalize_string_list(payload.get("files_written")) if payload else [],
                tests_run=_normalize_string_list(payload.get("tests_run")) if payload else [],
                followups=_normalize_string_list(payload.get("followups")) if payload else [],
                payload=payload,
            )

    return AgentResult(
        status="failed",
        summary="Agent output missing TASK COMPLETE / TASK BLOCKED / TASK FAILED marker",
        raw_output=raw_output,
        payload=payload or {},
    )
