"""Authenticated, stateless MCP transport for the bounded CNC tool catalog."""

import json

from fastapi import FastAPI
from mcp.server import Server, ServerRequestContext
from mcp.server.caching import CacheHint
from mcp.server.transport_security import RequestBodyLimitMiddleware, TransportSecuritySettings
from mcp.shared.exceptions import MCPError
from mcp.types import CallToolRequestParams, CallToolResult, ListToolsResult, PaginatedRequestParams, TextContent
from mcp_types import INVALID_PARAMS, INVALID_REQUEST, ErrorData, JSONRPCError, JSONRPCRequest, jsonrpc_message_adapter
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config.setting import Settings
from app.core.base_schema import AuthSchema
from app.core.database import async_db_session
from app.core.dependencies import AuthPermission, _authenticate
from app.core.exceptions import CustomException
from app.core.logger import logger

from .tools import TOOL_BY_NAME, TOOLS, ToolSpec

MAX_REQUEST_BYTES = 64 * 1024
AUTH_STATE_KEY = "cnc_mcp_auth"


def _rpc_error() -> JSONResponse:
    error = JSONRPCError(jsonrpc="2.0", id=None, error=ErrorData(code=INVALID_REQUEST, message="Invalid MCP request"))
    return JSONResponse(error.model_dump(by_alias=True), status_code=400)


def _tool_error(message: str) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=message)], is_error=True)


class PrivateAuthenticatedTransport:
    """Reuse current authentication and prevent SDK legacy validation from echoing secrets."""

    def __init__(self, app: ASGIApp, host: FastAPI) -> None:
        self.app = app
        self.host = host

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        scheme, _, token = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            response = JSONResponse({"error": "Authentication required"}, status_code=401, headers={"WWW-Authenticate": 'Bearer realm="cnc-mcp"'})
            await response(scope, receive, send)
            return
        try:
            async with async_db_session() as db, db.begin():
                auth = await _authenticate(token.strip(), db, self.host.state.redis)
        except CustomException:
            response = JSONResponse({"error": "Invalid or expired authentication"}, status_code=401, headers={"WWW-Authenticate": 'Bearer realm="cnc-mcp"'})
            await response(scope, receive, send)
            return
        except Exception:
            logger.warning("CNC MCP authentication unavailable")
            await JSONResponse({"error": "Authentication unavailable"}, status_code=503)(scope, receive, send)
            return

        scope.setdefault("state", {})[AUTH_STATE_KEY] = auth
        if request.method == "POST":
            body = await request.body()
            try:
                # SDK 2.3 legacy HTTP envelope errors include the invalid input by default.
                # Validate the same native envelope first, without returning/logging the exception.
                raw = json.loads(body)
                if isinstance(raw, dict) and "method" in raw and "id" in raw:
                    # The SDK union can reinterpret an invalid request ID as an
                    # extra field on a notification. Preserve the request shape.
                    JSONRPCRequest.model_validate(raw, by_name=False)
                else:
                    jsonrpc_message_adapter.validate_python(raw, by_name=False)
            except (ValidationError, ValueError, RecursionError):
                await _rpc_error()(scope, receive, send)
                return

            delivered = False

            async def replay() -> Message:
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return await receive()

            await self.app(scope, replay, send)
        else:
            await self.app(scope, receive, send)


class CncMCPServer:
    def __init__(self, host: FastAPI, config: Settings) -> None:
        self.server = Server(
            "cnc-management",
            version="1.0.0",
            instructions="Query CNC accounts and drawing metadata using list/detail tools. Account queries return encrypted passwords and account IDs. Use cnc_account_login to start/poll/verify/close a controlled login; it decrypts credentials internally and only READY means verified. Use cnc_account_decrypt_password with username (not id) only when a caller needs the plaintext password for a login form; it requires an exact, unique permitted account match. Never display or log that result. Login/decryption require account update permission and ownership checks. Login contacts external platforms and updates session state; other tools are read-only.",
            cache_hints={"tools/list": CacheHint(ttl_ms=0, scope="private"), "server/discover": CacheHint(ttl_ms=0, scope="private")},
            on_list_tools=self.list_tools,
            on_call_tool=self.call_tool,
        )
        self.server.streamable_http_app(
            streamable_http_path="/",
            stateless_http=True,
            json_response=True,
            max_request_body_size=MAX_REQUEST_BYTES,
            transport_security=TransportSecuritySettings(allowed_hosts=list(config.MCP_ALLOWED_HOSTS), allowed_origins=list(config.MCP_ALLOWED_ORIGINS)),
        )
        self.session_manager = self.server.session_manager
        self.app = RequestBodyLimitMiddleware(PrivateAuthenticatedTransport(self.session_manager.handle_request, host), max_body_size=MAX_REQUEST_BYTES)

    @staticmethod
    def _auth(ctx: ServerRequestContext) -> AuthSchema:
        if not isinstance(ctx.request, Request):
            raise MCPError(code=INVALID_PARAMS, message="Authentication required")
        auth = getattr(ctx.request.state, AUTH_STATE_KEY, None)
        if not isinstance(auth, AuthSchema) or auth.user.id < 1:
            raise MCPError(code=INVALID_PARAMS, message="Authentication required")
        return auth

    async def _allowed(self, auth: AuthSchema, spec: ToolSpec) -> bool:
        try:
            await AuthPermission([spec.permission])(auth=auth)
        except CustomException:
            return False
        return True

    async def list_tools(self, ctx: ServerRequestContext, params: PaginatedRequestParams | None) -> ListToolsResult:
        auth = self._auth(ctx)
        tools = [spec.tool() for spec in TOOLS if await self._allowed(auth, spec)]
        return ListToolsResult(tools=tools, ttl_ms=0, cache_scope="private")

    async def call_tool(self, ctx: ServerRequestContext, params: CallToolRequestParams) -> CallToolResult:
        auth = self._auth(ctx)
        spec = TOOL_BY_NAME.get(params.name)
        if spec is None or not await self._allowed(auth, spec):
            raise MCPError(code=INVALID_PARAMS, message="Tool unavailable")
        try:
            arguments = spec.arguments.model_validate(params.arguments or {})
        except ValidationError:
            return _tool_error("Invalid tool arguments; use the tool's input schema.")

        try:
            # Keep result validation inside the request transaction. Login owns
            # its separately committed, fenced repository transactions.
            async with async_db_session() as db, db.begin():
                result = await spec.execute(auth, db, arguments)
                response = CallToolResult(content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False))], structured_content=result)
            return response
        except CustomException:
            return _tool_error("Operation rejected by the existing business rules or data permissions.")
        except Exception:
            # Never pass a credential-bearing exception or traceback to Loguru.
            logger.warning("CNC MCP operation failed: tool={} actor_id={}", spec.name, auth.user.id)
            return _tool_error("Operation failed; contact the administrator.")
