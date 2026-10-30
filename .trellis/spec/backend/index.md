# Backend Development Guidelines

> Best practices for backend development in this project.

---

## Overview

This directory contains guidelines for backend development. Fill in each file with your project's specific conventions.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | To fill |
| [Database Guidelines](./database-guidelines.md) | ORM patterns, queries, migrations | To fill |
| [Error Handling](./error-handling.md) | Error types, handling strategies | To fill |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, forbidden patterns | To fill |
| [Logging Guidelines](./logging-guidelines.md) | Structured logging, log levels | To fill |
| [CNC Validation](./cnc-validation.md) | Fixed input/local-CAD research probes, identity/timeout guards and live/declaration boundaries | Source-backed; product integration pending |
| [Browser Executor](./browser-executor.md) | Shared Playwright scope, encrypted state, egress, intent and quote-validation contracts | Component scope; provider integration pending |
| [CNC Account Login](./cnc-account-login.md) | Controlled login APIs, account privacy, fenced leases, provider identity, optional-resource denial and browser UI | D-18 implemented; live deployment/auth validation separate |
| [CNC Auto Quote](./cnc-auto-quote.md) | Configuration quote APIs, durable runs/intents, current RBAC, same-owner lifecycle and result truthfulness | Integration in progress; provider live acceptance tracked separately |
| [CNC Batch](./cnc-batch.md) | Durable batch admission, frozen quantities, dispatcher ownership, atomic completion and compatible migration | T1 local SQLite/isolated PostgreSQL checks documented; live acceptance pending |
| [CNC Recovery](./cnc-recovery.md) | Structured error classification, retry budgets, uncertain intent fencing and recovery scanner | T2 local regressions and recovery suite documented |
| [CNC Schedules](./cnc-schedules.md) | Periodic monitoring plans, anchor slot alignment, round admission guards and scheduler integration | T3 local regressions and monitor suite documented |
| [DeerFlow Source Integration](./ai-agent.md) | Selected Agent source adapted to FastAPI layers, async lifecycle, identity/model/checkpoint and domain ownership contracts | Offline integration in progress; Agno remains default and source startup is gated |
| [CNC MCP Server](./cnc-mcp.md) | Embedded MCP Server, account/drawing queries, controlled login, explicit password decryption and existing auth/data scopes | Implemented; isolated protocol/database validation; live login acceptance separate |

---

## How to Fill These Guidelines

For each guideline file:

1. Document your project's **actual conventions** (not ideals)
2. Include **code examples** from your codebase
3. List **forbidden patterns** and why
4. Add **common mistakes** your team has made

The goal is to help AI assistants and new team members understand how YOUR project works.

---

**Language**: All documentation should be written in **English**.
