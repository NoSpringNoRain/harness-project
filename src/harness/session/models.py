from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class SessionState(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    READING_CODE = "reading_code"
    MODIFYING = "modifying"
    TESTING = "testing"
    PR_CREATED = "pr_created"
    WAITING_APPROVAL = "waiting_approval"
    MERGED = "merged"
    DEPLOYED = "deployed"

class SessionStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class EventType(str, Enum):
    STATE_TRANSITION = "state_transition"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"

@dataclass
class Session:
    session_id: str
    task_description: str
    current_state: SessionState
    status: SessionStatus
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class Event:
    event_id: str
    session_id: str
    sequence_number: int
    event_type: EventType
    payload: dict
    timestamp: datetime = field(default_factory=datetime.now)

