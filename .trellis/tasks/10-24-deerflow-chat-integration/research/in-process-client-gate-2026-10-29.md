# In-process DeerFlowClient gate (2026-10-29)

> Historical Client-only gate: the user subsequently requested source integration into the existing FastAPI architecture. This report remains evidence about the pinned Client, not a blocker requiring new Client APIs for the source-based design. See the [current decision and source map](../../10-24-deerflow-cnc-agent/research/source-integration-replan-2026-10-29.md).

## Scope and user decision

The user requested implementation of this existing chat-integration task and
chose to retain the in-process architecture and all acceptance criteria. If
the official in-process Client cannot meet them, stop and explain instead of
using a separate process or weakening cancellation. This decision supersedes
the historical “planning/cleanup only” authorization for this request, but it
does not remove the implementation gates in the task.

## Evidence

- The existing application still runs Agno chat. `deerflow` is not installed
  in `backend/.venv`, and `backend/pyproject.toml` has no DeerFlow dependency.
  The required Lead integration has not been implemented.
- The official source at commit `24f15cc4790f5b0a50f55332f77f4a2eeb35fdf1`
  was read directly from GitHub. The `client.py` SHA-256 is
  `a89b5da4bf65f0ac43f5b8d7bea62261c1661f49bb92568d5b6eccb48d2d5fb6`.
  Its public `DeerFlowClient.stream()` is a synchronous generator. Its public
  methods include no async stream or cancellation operation. It internally
  calls the synchronous agent stream and advances it with `next()`.
- The same commit's official TUI explicitly documents that an interrupted
  worker cannot be killed and stops only on the next stream event. It blocks a
  new run on the same thread while the old worker could still checkpoint.
  This is incompatible with CA-02's real-stop requirement before the first
  token and the one-second convergence target.
- A local standard-library experiment held a synchronous generator inside
  `next()` on one thread and called `close()` from another. Python returned
  `ValueError: generator already executing`. This illustrates why closing the
  iterator from the WebSocket task does not stop a blocked generator. It is not
  a test of a real provider or proof about remote provider billing.
- The official `deerflow.runtime.runs.run_agent` is an independent async
  Gateway-style path requiring an `agent_factory`; the pinned Client itself
  documents that its synchronous stream does not use that pipeline. The Client
  does not expose the assembled agent through a public method. Substituting the
  Gateway path, accessing Client private internals, or creating another agent
  factory would change the agreed design rather than establish that the
  requested Client supports cancellation.
- The same source exposes `push_current_app_config` / `pop_current_app_config`
  for execution-context scoped configuration. These may be relevant to
  personal-model isolation, but were not executed against the real Client and
  are not evidence that concurrent model isolation is solved.
- The pinned harness distribution is `deerflow-harness==2.1.0` and requires
  `deerflow-extension-api==0.2.9`; both packages returned HTTP 404 from the
  public PyPI JSON API during this check. A reproducible official-source build
  remains to be verified. Existing installed LangGraph/LangChain versions do
  not meet the pinned harness requirements.

## Result

The stop-before-first-token gate is not met through the verified public Client
API. Task status remains `planning`; no product code, dependency, migration,
user database, model service, or existing chat behavior was changed. No live
model, provider, or full product acceptance test was run. Reassess when the
official Client provides a verified in-process cancellation interface, or when
the user explicitly changes the architecture or acceptance requirements.

Sources:

- https://github.com/bytedance/deer-flow/blob/24f15cc4790f5b0a50f55332f77f4a2eeb35fdf1/backend/packages/harness/deerflow/client.py
- https://github.com/bytedance/deer-flow/blob/24f15cc4790f5b0a50f55332f77f4a2eeb35fdf1/backend/packages/harness/deerflow/tui/app.py
- https://github.com/bytedance/deer-flow/blob/24f15cc4790f5b0a50f55332f77f4a2eeb35fdf1/backend/packages/harness/deerflow/runtime/runs/worker.py
