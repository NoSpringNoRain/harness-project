# harness-project

A from-scratch **agent harness** for autonomous code changes: given a task
("fix this failing test", "add this endpoint"), an agent reads code, edits
files, runs tests, iterates on failures, and opens a PR for human approval.

The goal is not another wrapper around a model API. It is the part around the
model that makes agents **reliable**: durable session state, crash recovery,
bounded loops, scoped tool permissions, and human checkpoints.

> Status: early. The session layer is done; the agent loop is in progress.
> See [Status](#status).

---

## Why

Running coding agents in real work, the failures are rarely about model
quality. They come from the missing system around the model:

- **Lost state.** A long session crashes or runs out of context, and the
  agent no longer knows what it already did.
- **Unbounded loops.** A test-fix cycle keeps retrying the same failure.
- **Out-of-scope changes.** The agent edits, creates, or deletes files it
  had no reason to touch.
- **No audit trail.** Afterwards, nobody can tell what the agent did, in
  what order, or why.

This project builds those missing pieces one at a time, starting with the
foundation everything else depends on: a durable session log.

---

## Status

| Component | Status |
|---|---|
| Session & event models (`session/models.py`) | ✅ Done |
| Append-only session log with replay, crash-safe recovery, and schema validation (`session/log.py`) | ✅ Done |
| Harness loop (ReAct: call model → route tool calls → retry/fallback → max-iteration guard) | 🚧 In progress |
| Tools with tiered permissions (read-only automatic / writes audited / merge & deploy human-approved) | ⏳ Planned |
| Sandbox for code execution and tests | ⏳ Planned |
| Context management (compaction, prompt caching) | ⏳ Planned |
| Evals (task success rate, turns and cost per task) | ⏳ Planned |

---

## Architecture

```
            ┌──────────────────────────────────────────┐
 task ───▶  │  Harness loop (ReAct)                     │ ───▶ PR (human approves)
            │  think → call tool → observe → repeat     │
            │  · max iterations · retry / fallback      │
            └──────┬───────────────────────┬───────────┘
                   │ every step            │ tool calls
                   ▼                       ▼
         ┌──────────────────┐    ┌───────────────────────────┐
         │  Session log      │    │  Tools (tiered)            │
         │  append-only      │    │  read-only → automatic     │
         │  JSONL events     │    │  write     → audited       │
         │  replay / recover │    │  merge/deploy → human      │
         └──────────────────┘    └───────────────────────────┘
```

The task follows an explicit state machine:

```
created → planning → reading_code → modifying → testing ─┬─▶ pr_created → waiting_approval → merged → deployed
                                        ▲                │
                                        └── tests fail ──┘   (max attempts reached → failed)
```

---

## Design decisions

### Event sourcing for sessions
The harness never overwrites session state. Every change — a state
transition, a model call, a tool call, a tool result, an error — is
**appended** as an event. The current state is rebuilt by replaying events
from the start. This gives:

- **Crash recovery:** restart the process, replay the log, continue from the
  last event.
- **Traceability:** the log is a complete, ordered record of what the agent
  did — useful for debugging and for audit.
- **A clean extension point:** snapshots, evals and dashboards can all be
  built by reading the same log.

It is the same idea as a database write-ahead log.

### JSONL, one file per session
Each event is one JSON object on its own line in `sessions/<session_id>.jsonl`.

- Appending is cheap and never touches existing lines.
- A crash during a write can only damage the **last** line; everything
  before it stays valid.
- The file can be read line by line.

### Failure handling on replay
| Situation | Behavior | Why |
|---|---|---|
| Last line is invalid JSON | Skip it, warn | A crash mid-write can only truncate the line being written |
| A middle line is invalid JSON | Raise `ValueError` | Not explainable by a crash — the log can't be trusted |
| Valid JSON but not a valid event (missing/extra field, wrong type, unknown event type) | Raise `ValueError` with the line number | A crash produces truncated JSON, never a well-formed wrong record |
| Gap or duplicate in `sequence_number` | Raise `ValueError` | Replay would rebuild the wrong state |

Python dataclasses don't validate types, so events are validated explicitly
on read (e.g. a `sequence_number` of `"1"` is rejected rather than silently
accepted).

### Not built yet, by choice
- **Snapshots:** replay is O(n). The plan is to save derived state every N
  events and replay only the tail; events are never deleted.
- **Multiple writers:** one harness process owns one session for now.
- **A database:** the `append_event` / `replay_session` interface is what
  matters; it can move to Postgres later without changing callers.

---

## Repository layout

```
src/harness/
  session/
    models.py   # Session, Event dataclasses; SessionState, SessionStatus, EventType enums
    log.py      # append_event(), replay_session()
tests/
  test_log.py   # round-trip, missing session, crash-truncated line, invalid events
```

---

## Running the tests

```bash
pip install pytest
PYTHONPATH=src pytest -q
```

(Windows PowerShell: `$env:PYTHONPATH="src"; pytest -q`)

---

## Roadmap

1. **Harness loop:** call the model with a tool list, route tool calls,
   log every step, retry with fallback, stop at a max iteration count.
2. **Tools with tiered permissions:** read-only tools run automatically;
   write tools are scoped and audited; merge/deploy always require a human.
3. **Structured tool errors:** each failure says whether it is retryable,
   so the loop decides retry vs. fallback vs. stop on evidence, not guesswork.
4. **Sandbox** for running code and tests in isolation.
5. **Evals:** a small benchmark of code-change tasks reporting success rate,
   turns, and cost per task.
