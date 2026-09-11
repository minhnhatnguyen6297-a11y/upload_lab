# DesktopCommand Electron POC — measurement report

Date: 2026-09-11  
Branch: `codex/desktop-command-poc`  
Baseline commit: `0c4edf78f708c7fcf3a9a03ba93dc42a0bb85d62`  
Conclusion: **ITERATE** (POC boundary works; no production adoption decision).

## Scope and safety

- The Electron shell starts a Python FastAPI sidecar on `127.0.0.1` and keeps
  the bearer token in the Electron main process.
- Manual smoke used `DESKTOP_COMMAND_POC_FAKE_WORKER=1`; it did not start
  Playwright, open the provincial website, use credentials, or capture customer
  data.
- The existing PySide6 UI and production startup files were not changed.

## Verification matrix

| Check | Result | Evidence |
|---|---|---|
| Electron package launch | Pass | `package.json` declares `main.js`; `npm start` opens the POC window |
| Renderer load | Pass | page URL is the worktree `renderer.html`; body contains Start/Cancel/Scan/status controls |
| Sidecar readiness | Pass | `GET /healthz` returns `{"status":"ok","contract_version":"v0.experimental"}` |
| Auth and secret boundary | Pass | Python suite and Node suite reject missing bearer and sensitive payload keys |
| Queue-only fake-worker smoke | Pass | `start_upload` reaches `waiting_user` without a browser |
| Duplicate command behavior | Pass | registry/API tests return the same job for a repeated command id |
| Scan mapping | Deliberately unavailable | returns structured `scan_unavailable`; no business mapping was invented |
| Active upload RSS | Not measured | would require a disposable browser session and approved test data |
| Restart/shutdown timings | Not measured | lifecycle is covered by code paths, but no stable benchmark was collected |

## Windows startup and memory sample

Measurements were taken on the same worktree and machine using a visible local
launch, polling for a native window handle, and summing `WorkingSet64` for the
process tree. They are directional POC measurements, not release benchmarks.

| App | Startup to window | Idle process-tree RSS | Installed directory |
|---|---:|---:|---:|
| Electron shell + fake sidecar | 2.6 s | 341.4 MiB (6 processes) | 263.2 MiB (`node_modules` included) |
| PySide6 `ui_runner.py` | 0.5 s to process/window observation | 179.1 MiB (1 process observed) | not measured |

The Electron sample is approximately 1.9x the observed PySide6 RSS and has a
larger startup/install footprint. The comparison is not yet apples-to-apples:
the Electron sample includes Chromium helper processes and the Python sidecar,
while active browser RSS and a repeatable PySide6 cold-start protocol remain
unmeasured.

## Recommendation

Keep the localhost FastAPI + preload/IPC boundary as the experimental seam and
iterate the POC only if a shared desktop shell is still valuable. Before any
adoption decision, repeat measurements with a fixed cold-start protocol,
measure active upload/browser memory, exercise sidecar restart and shutdown,
and compare a real user flow in a disposable environment. This report does not
authorize a PySide6 rewrite, website embedding, or a production API.
