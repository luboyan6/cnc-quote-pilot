# Chat integration baseline — 2026-10-29

The user has authorized implementation of the existing Agent upgrade task tree;
the Lead contract and its offline gates precede chat integration.

- `ai/chat/controller.py` currently consumes the entire `chat_query` stream
  inside the same loop that receives WebSocket messages. A stop message cannot
  be received while a slow generation is in progress. Separate receive,
  generation and bounded send ownership are needed, with one terminal event.
- `_ensure_session` in `ai/chat/service.py` returns a supplied session ID
  without verifying ownership. The new executor must verify the authenticated
  numeric actor's ownership before executing or accessing checkpoints.
- `get_user_model_config` returns `None` both for a system default and for an
  active personal model whose configuration is missing. The new executor must
  distinguish these cases and reject the latter rather than substitute a model.
  The real system default is `settings.OPENAI_MODEL`, `OPENAI_BASE_URL`,
  `OPENAI_API_KEY`, temperature 0.7; these are not checkpoint data.
- The Vue chat currently switches session IDs and clears messages without a
  generation fence. A late WebSocket chunk or detail response can update the
  new view. Preserve failed drafts and prevent stale event application.
- No existing tests under `backend/tests` reference `ChatService`,
  `AgnoFactory`, or `/ai/chat`; add meaningful transport, ownership and legacy
  regression tests as part of the implementation.

Focused UI guidance: stream status text, give icon-only controls accessible
names, and clean up watchers/subscriptions and socket handlers on unmount or
session change. Keep existing Vue/Element Plus conventions.
