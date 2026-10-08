---
name: start-ui
description: Build and start the local python-cad viewer. Use when the user explicitly asks to start, launch, serve, open, or run the local CAD UI.
---

# Start UI

Act only after the user explicitly asks to start or launch the viewer. Use the
requested port, or port 8080 by default. Build first unless the user explicitly
asks to reuse existing generated output.

Run this from the repository root in a managed long-running terminal session:

```bash
.venv/bin/python-cad serve --build --port 8080
```

Replace `8080` when the user requests another port. Wait for the ready message
and retain the terminal session so it can be stopped with Ctrl-C. If the command
runner must detach the process, record its PID in `.makeitours/ui-server.pid` and
its output in `.makeitours/ui-server.log`; never launch an untracked background
server.

Report the URL. If a managed viewer is already running, report that result
instead of starting a duplicate. Do not use broad process discovery or
terminate unrelated processes.
