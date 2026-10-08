---
name: stop-ui
description: Stop the managed local python-cad viewer. Use when the user explicitly asks to stop, shut down, terminate, or close the local CAD UI server.
---

# Stop UI

Act only after the user explicitly asks to stop the viewer.

Send Ctrl-C to the managed terminal session that started this viewer. If no live managed session exists, read the
PID from `.makeitours/ui-server.pid`, then run:

```bash
UI_SERVER_PID="$(.venv/bin/python -c 'import json; print(json.load(open(".makeitours/ui-server.pid"))["pid"])')"
ps -p "$UI_SERVER_PID" -o command=
kill -TERM "$UI_SERVER_PID"
```

Run `kill` only after inspecting the `ps` output and confirming that exact PID
is a `python-cad ... serve` process. Remove the stale PID record after the
process stops. If the record is missing, invalid, stale, or identifies another
command, do not kill anything.

Report whether the viewer stopped, was already stopped, or had a stale PID
record. Never search broadly for Python processes, kill by port, or terminate a
process that is not the recorded managed viewer.
