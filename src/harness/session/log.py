import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .models import Event, EventType

LOG_DIR = Path("sessions")

def _log_path(session_id: str, log_dir: Path) -> Path:
    return log_dir / f"{session_id}.log"

def _event_to_dict(event: Event) -> dict:
    event_dict = asdict(event)
    event_dict["timestamp"] = event.timestamp.isoformat()
    return event_dict

def _dict_to_event(d: dict) -> Event:
    d["timestamp"] = datetime.fromisoformat(d["timestamp"])
    d["event_type"] = EventType(d["event_type"])
    return Event(**d)

def append_event(event: Event, log_dir: Path = LOG_DIR) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = _log_path(event.session_id, log_dir)

    line = json.dumps(_event_to_dict(event))

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()

def replay_session(session_id: str, log_dir: Path = LOG_DIR) -> list[Event]:
    log_path = _log_path(session_id, log_dir)
    if not log_path.exists():
        return []

    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    events: list[Event] = []
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue

        try:
            event_dict = json.loads(line)
        except json.JSONDecodeError:
            if i == len(lines) - 1:
                # Last line might be incomplete due to a crash, ignore it
                print(f"warning: ignoring incomplete last line in {log_path}")
                break

            raise ValueError(f"corrupted line {i + 1} in {log_path}")

        event = _dict_to_event(event_dict)

        expected = len(events) + 1
        if event.sequence_number != expected:
            raise ValueError(
                f"sequence gap in {log_path}: expected {expected}, got {event_dict.get('sequence_number')}")          

        events.append(event)

    return events
