# DeerFlow source provenance

Reference repository: https://github.com/bytedance/deer-flow, fixed commit
`f6fe1e9c9e029bf22b8e2eb8e2e23e1258cf0814`. SHA-256 values below are for
the original files at that commit. Original license and copyright notices are
preserved in `DEERFLOW_LICENSE.txt`.

All paths in the source column are relative to
`backend/packages/harness/deerflow/` in the upstream tree. These adaptations
are intentionally narrower than the upstream feature set; they are not an
import of the upstream package or a claim of full behavioral compatibility.

| Source | SHA-256 | Project component and change |
| --- | --- | --- |
| agents/factory.py | b7c2d6a4502771cfd66204177d3259459c98830c76b553f4d26a659ff7f2cebc | `graph.py`: explicit model/tools/middleware/state/checkpointer assembly via LangChain; no features, delegation, extensions or global config. |
| agents/thread_state.py | 2adb816b22200f472dea71d41ea14935cb92784ee08e78c1f4b34aa89f915a32 | `state.py`: full message checkpoint and active names only; sandbox, memory, summaries, delta and delegation omitted. |
| agents/middlewares/skill_activation_middleware.py | d56be0375b4ea5c3c6d0ab1ab931716e1b68667178567aa575403c18d17e388f | `middleware.py`: explicitly selected names, current catalog read, deduplicated activation and request-only prompt injection; no slash parser, remote storage or secret binding. |
| agents/middlewares/system_message_coalescing_middleware.py | cadb241c22f122e6d923c96d4a7c58d2618d77d81b9771a92debf81810a98dbf | `middleware.py`: combine system messages for the model request, leaving checkpoint unchanged; no dynamic date reminder logic. |
| agents/middlewares/dangling_tool_call_middleware.py | cc574204f0dfeba8d5207281280c28dd0b9fa5d7165e0bf0c0e076ec37c4ee15 | `middleware.py`: request-only insertion of missing results and dropping orphans; does not implement the upstream malformed provider payload/ID repair machinery. |
| agents/middlewares/tool_error_handling_middleware.py | c96affc4dfb65cfc660770dbd45052851d1de5529069a855c89b5f270d602c69 | `middleware.py`: safe fixed error responses, cancellation/control-flow propagate; no upstream exception detail, secrets or subagent metadata. |
| skills/frontmatter.py | bf8fdd9e6f31caef2ff837cd0ebcb703dd8911266ffbe171049b840f4bf3db5d | `skills/catalog.py`: fenced YAML parsing, BOM handling and bounded local read. |
| skills/parser.py | c56963d03de480250228912264b5b36f26eb8ee0664825f0c6c0d4d2cc8acabb | `skills/catalog.py`: required metadata, names and allowed tools; only literal tool names/list or whitespace string accepted, not portable aliases, scoped parenthesized commands, installation or secrets. |
| skills/validation.py | d6ea2ff4341db6ab7f15a13f3b9f67dff995698f770d1a754d9a63da923ce847 | `skills/catalog.py`: constrained names, descriptions, size and root checks; unsupported secret declarations rejected, not silently interpreted. |

Behavior tests are in `backend/tests/ai/agent/`: catalog parsing and path
escape, actual compiled graph → published skill → owned CNC service record,
permission removal, local HTTP disconnect, cancellation and PostgreSQL saver
reopening. The local `AgentService`, event envelope, identity adapters and
Windows PostgreSQL bridge are project-specific implementations, not copied
DeerFlow files.
