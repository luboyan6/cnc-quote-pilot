# DeerFlow pinned egress component

Only `egress.py` is vendored from:

- Repository: https://github.com/bytedance/deer-flow
- Commit: `f6fe1e9c9e029bf22b8e2eb8e2e23e1258cf0814`
- Path: `backend/packages/harness/deerflow/community/browser_automation/egress.py`
- License: MIT, full unmodified notice in [DEERFLOW-LICENSE](DEERFLOW-LICENSE).
- Dependencies: Python standard library only. No harness, Agent, or thread runtime.

Local adaptations (2026-10-21):

1. Restrict CONNECT port to 443 before resolution/connection.
2. Replace DNS/connection diagnostic logs containing host/error details with fixed
   reason text; no raw browser destination, credential or exception is emitted.
3. Track accepted handler tasks, cancel/join them on close, and recheck closed
   state after DNS. A resolving handler must not connect after session cleanup.
4. Surface bounded handler/server close failures with a fixed error instead of
   suppressing them; the session still closes its other resources and reports
   cleanup failure. This exposes observed Windows Proactor transport failures.
5. Formatting/import ordering follows the business backend's Ruff configuration.

Windows accepted-stream adaptation (2026-10-22):

- On Windows only, `start_windows_server` in the parent module replaces the
  listener setup; Unix retains the original `asyncio.start_server`. SOCKS
  negotiation, vetted resolver, literal-IP connect and port policy are unchanged.
- Public `loop.sock_accept` accepts our loopback socket. Public `socket.detach`
  transfers its handle to our `_AcceptedSocket` before public
  `asyncio.open_connection(sock=...)` transfers ownership to Streams. Failed
  wrapper construction closes the detached handle with `socket.close(handle)`.
- The owned socket's shutdown ignores only `ConnectionResetError(winerror=10054)`.
  This permits Python 3.12 Proactor's subsequent normal close; all other shutdown
  errors propagate and set a separate outcome record checked by the listener.
  No socket owned by an existing transport is inspected or manually closed.
- `wait_closed` may return terminal Proactor read reset 64 after closing. Only
  the identical `ConnectionResetError(winerror=64)` in public `reader.exception()`
  is classified as that delivered read result. Independent/unknown close errors,
  shutdown errors (including 10053), callback faults and timeouts still fail
  cleanup; the independent shutdown record prevents read reset masking them.
- The adapter owns raw sockets for callbacks not yet started, accept/handoff
  tasks and writer closure through `wait_closed`, with a bound inside the proxy's
  existing close timeout. There is no stdlib/private transport monkeypatch,
  global exception handler, alternate SOCKS implementation or thread runtime.

`BrowserPolicy.resolve` is supplied as the original resolver hook. It validates
exact trusted host membership and rejects every non-public/mixed DNS answer.
The proxy passes only validated literal IPs to `asyncio.open_connection`; it
does not ask Chromium to re-resolve the host. The listener is session-local
loopback with no authentication, and must stay inside the isolated browser
worker's trust boundary. This is not an external general-purpose proxy service.
