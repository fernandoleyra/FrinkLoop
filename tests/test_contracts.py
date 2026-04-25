from core.contracts import parse_agent_output


def test_parse_agent_output_complete():
    result = parse_agent_output(
        'RESULT_JSON: {"summary":"built auth endpoint","files_written":["src/auth.py"],"tests_run":["pytest tests/test_auth.py"],"followups":[]}\n'
        "Implemented feature\n"
        "TASK COMPLETE: built auth endpoint"
    )
    assert result.status == "complete"
    assert result.summary == "built auth endpoint"
    assert result.files_written == ["src/auth.py"]
    assert result.tests_run == ["pytest tests/test_auth.py"]


def test_parse_agent_output_blocked():
    result = parse_agent_output(
        'RESULT_JSON: {"summary":"missing API credentials","blocker_reason":"missing API credentials","files_written":[],"tests_run":[],"followups":["wait for secret"]}\n'
        "Tried two approaches\n"
        "TASK BLOCKED: missing API credentials"
    )
    assert result.status == "blocked"
    assert result.blocker_reason == "missing API credentials"
    assert result.followups == ["wait for secret"]


def test_parse_agent_output_missing_marker_fails():
    result = parse_agent_output("I changed some files but forgot the marker")
    assert result.status == "failed"


def test_parse_agent_output_invalid_payload_fails():
    result = parse_agent_output("RESULT_JSON: {not json}\nTASK COMPLETE: done")
    assert result.status == "failed"


def test_parse_agent_output_complete_without_colon_marker():
    result = parse_agent_output(
        'RESULT_JSON: {"summary":"built auth endpoint","files_written":["src/auth.py"],"tests_run":["pytest tests/test_auth.py"],"followups":[]}\n'
        "Implemented feature\n"
        "TASK COMPLETE"
    )
    assert result.status == "complete"
    assert result.summary == "built auth endpoint"
    assert result.files_written == ["src/auth.py"]


def test_parse_agent_output_from_result_json_markdown_section():
    raw_output = (
        "**RESULT_JSON**\n"
        "```json\n"
        "{\n"
        "  \"summary\": \"Project plan created\",\n"
        "  \"plan_markdown\": \"memory/plan.md\",\n"
        "  \"tasks_board\": \"memory/tasks.json\",\n"
        "  \"decisions_entry\": \"memory/decisions.md\"\n"
        "}\n"
        "```\n"
        "TASK COMPLETE\n"
    )
    result = parse_agent_output(raw_output, task_type="plan")
    assert result.status == "complete"
    assert result.summary == "Project plan created"
    assert result.payload["plan_markdown"] == "memory/plan.md"


def test_parse_agent_output_plan_payload_without_marker_completes():
    result = parse_agent_output(
        'RESULT_JSON: {"summary":"Created plan","plan_markdown":"# plan","tasks_board":{"project":"my-app","milestones":[]}}',
        task_type="plan",
    )
    assert result.status == "complete"
    assert result.summary == "Created plan"
    assert result.payload["plan_markdown"] == "# plan"
