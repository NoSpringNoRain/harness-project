from harness.session.models import Event, EventType
from harness.session.log import append_event, replay_session

def make_events(session_id: str) -> list[Event]:
    return [
        Event(
            event_id=f"{session_id}-1",
            session_id=session_id,
            sequence_number=1,
            event_type=EventType.STATE_TRANSITION,
            payload={"from": "created", "to": "planning"},
        ),
        Event(
            event_id=f"{session_id}-2",
            session_id=session_id,
            sequence_number=2,
            event_type=EventType.LLM_CALL,
            payload={"prompt": "Hello, world!"},
        ),
        Event(
            event_id=f"{session_id}-3",
            session_id=session_id,
            sequence_number=3,
            event_type=EventType.TOOL_CALL,
            payload={"tool_name": "my_tool", "args": {"x": 42}},
        ),
    ]

def test_append_and_replay(tmp_path):
    events = make_events("s1")

    for event in events:
        append_event(event, log_dir=tmp_path)

    replayed_events = replay_session("s1", log_dir=tmp_path)

    assert len(replayed_events) == len(events)
    assert replayed_events == events

def test_missing_session_returns_empty_list(tmp_path):
    replayed_events = replay_session("missing_session", log_dir=tmp_path)
    assert replayed_events == []

def test_corrupted_log_raises_value_error(tmp_path):
    events = make_events("s2")

    # Corrupt the log by appending an invalid JSON line
    log_path = tmp_path / "s2.log"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("{invalid_json}\n")

    for event in events:
        append_event(event, log_dir=tmp_path)

    try:
        replay_session("s2", log_dir=tmp_path)
        assert False, "Expected ValueError due to corrupted log"
    except ValueError as e:
        assert "corrupted line" in str(e)

def test_incomplete_last_line_is_ignored(tmp_path):
    events = make_events("s3")

    for event in events:
        append_event(event, log_dir=tmp_path)

    # Corrupt the log by appending an incomplete JSON line
    log_path = tmp_path / "s3.log"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write('{"event_id": "s3-4", "session_id": "s3", "sequence_number": 4')  # Incomplete Event JSON

    replayed_events = replay_session("s3", log_dir=tmp_path)

    # The last incomplete line should be ignored, so we should get back the original events
    assert len(replayed_events) == len(events)
    assert replayed_events == events