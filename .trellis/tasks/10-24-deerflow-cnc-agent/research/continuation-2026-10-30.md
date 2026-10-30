# Agent upgrade continuation — 2026-10-30

> Paused at the user's request on 2026-10-30. Do not resume implementation or
> provider actions until the user asks to continue. The user chose to preserve
> old Agno records without migrating them; the Xometry controlled-login step
> was not completed in this continuation.

This records incremental work, not acceptance of the parent task. The default
chat engine remains Agno; the source-engine startup gate remains closed.

## Chat attachments

- Source WebSocket protocol 2 accepts up to eight distinct private drawing
  upload request UUIDs. Before starting the graph, the service reloads the
  actor and drawing-detail permission and resolves each READY owned upload
  through the existing private upload service, which rechecks bytes and SHA-256.
  Only part ID, hash and byte size enter the graph; this is not third-party
  transfer authorization.
- Vue uploads real STEP bytes with a stable UUID per file, retains the draft
  until `turn.started`, and ignores late upload results after stop or session
  switch. Unversioned chat retains its previous attachment restriction.
- Focused offline tests cover owner isolation, file modification, revoked
  permission, invalid/duplicate references, retry identity, and late results.

## Read-only domain tools

The existing catalog/tool builder now exposes permission-filtered quote result,
statistics/history, batch status/items, and monitoring status/rounds. They use
the existing domain services/repositories and current owner checks. Reporting
remains actor-private even for a superuser; private evidence paths and monitor
snapshots are not returned. Quote writes, batch admission/cancellation and
schedule mutation tools have not yet been delivered.

An authorized quote-result tool can now emit a numeric reference to an existing
available private evidence image. Chat fetches it through the authenticated
`private_only=true` result endpoint and aborts/releases the Blob on session
switch. Checkpoint repair stores numeric references in the visible assistant
message projection, so history refresh and Agno rollback can restore cards.
Migration `a816e3b61030` was validated against isolated SQLite and PostgreSQL;
it has not been applied to the user's configured database. Provider capture,
redaction and atomic evidence publication are not established by this read path.

## Validation

- Combined offline backend run: 150 passed, 34 skipped, 76 subtests passed;
  five existing SQLAlchemy metadata-copy warnings. Skips include opt-in
  PostgreSQL cases and a Windows symlink privilege case. A separate disposable
  PostgreSQL run subsequently passed all 34 checkpoint and batch cases.
  The test server was stopped; no configured application database was used.
- After the later evidence-projection changes, the AI/upload/results suite
  passed 103 tests with 3 skips and 76 subtests. The PostgreSQL checkpoint and
  new projection migration were separately exercised on the disposable server.
- Chat/result frontend tests: 18 passed; Vue type-check, production build,
  scoped ESLint, Stylelint and Prettier checks passed. Backend scoped Ruff and
  basedpyright passed.
- The latest focused chat tests passed after evidence-history restoration.
  The final frontend production build was interrupted when the user requested
  pause; an earlier build passed before those latest UI changes. Re-run the
  build and final scoped checks on resume.
- With only synthetic prompts/data, the configured model activated
  `cnc-quote-report`, called `cnc_quote_statistics` and completed. A separate
  stop probe observed the HTTP request body sent before the first text and a
  unique stopped event after local cleanup; another stopped after first text.
  Observed stop times were below one second. Sending a request body is not
  proof of remote receipt; these single runs do not prove every cleanup is
  bounded or validate the browser UI/production data.

## Remaining gates

- Existing Agno sessions use mutable usernames, while current account update
  permits renaming. On 2026-10-30 the user chose not to migrate old chat and
  to preserve the old records. The source engine therefore does not guess a
  historical username-to-owner mapping or import old sessions. Offline rollback
  readback now lists owned source projections as read-only alongside Agno
  sessions, with namespaced IDs and stable pagination; it cannot repair an
  unmaterialized checkpoint while the source engine is stopped.
- Review rollback behavior when source-chat tables exist at revision
  `3a29b7e61029` but the new `evidence_result_ids` column is absent: current
  ORM reads expect the new column. Do not upgrade the user's database
  automatically; decide and test compatible readback or explicit migration
  handling before enabling the new engine.
- Complete the new write tools and their durable admission/stop boundary,
  provider evidence capture/publication, model/UI/restart integration, and live
  provider acceptance. Existing unresolved provider intentions remain intact;
  JLC effective-parameter readback remains gated. A reference estimate is not
  formal-price acceptance.
- The working tree contains pre-existing uncommitted changes from this and
  other tasks; none were reverted or committed in this continuation.
