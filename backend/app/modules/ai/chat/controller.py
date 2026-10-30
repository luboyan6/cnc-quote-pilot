import asyncio
import json
import uuid
from contextlib import aclosing
from dataclasses import dataclass, field
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Path, Query, Request, Security, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.common.response import ResponseSchema, SuccessResponse
from app.config.setting import settings
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.database import async_db_session
from app.core.dependencies import AuthPermission, get_current_user, redis_getter, websocket_authenticate
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.core.router_class import OperationLogRoute

from .rollback_sessions import RollbackSessionService
from .schema import (
    AiChatRequestSchema,
    AiChatResponseSchema,
    AiModelConfigListResponse,
    AiModelConfigSchema,
    ChatCapabilitiesSchema,
    ChatQuerySchema,
    ChatSessionCreateSchema,
    ChatSessionOutSchema,
    ChatSessionQueryParam,
    ChatSessionUpdateSchema,
)
from .service import AiModelConfigService, ChatService, get_user_model_config
from .source_sessions import SourceSessionService

ChatRouter = APIRouter(route_class=OperationLogRoute, prefix="/chat", tags=["AI管理"])

# WebSocket 聊天所需权限（与 HTTP 对话端点保持一致）
_WS_CHAT_PERMISSION = "module_ai:chat:query"


def _has_chat_permission(auth: AuthSchema) -> bool:
    """校验当前用户是否具备 AI 聊天权限（超管/通配权限直接放行）"""
    return _has_permission(auth, _WS_CHAT_PERMISSION)


def _has_permission(auth: AuthSchema, required: str) -> bool:
    user = auth.user
    if user.id <= 0:
        return False
    if user.is_superuser:
        return True
    permissions = set(auth.permissions or [])
    return "*:*:*" in permissions or required in permissions


def _session_service(auth: AuthSchema) -> RollbackSessionService | SourceSessionService:
    return SourceSessionService(auth) if settings.AI_CHAT_ENGINE == "deerflow_source" else RollbackSessionService(auth)


def _source_http_chat(request: Request, auth: AuthSchema, permission: str = _WS_CHAT_PERMISSION):
    # Imported only when the gated optional Agent dependency is enabled.
    from .source_service import SourceChatService

    token = request.headers.get("authorization", "")

    async def refresh_auth() -> AuthSchema:
        async with async_db_session() as db:
            current = await get_current_user(db=db, redis=request.app.state.redis, token=token)
        if current.user.id != auth.user.id or not _has_permission(current, permission):
            raise PermissionError("CHAT_OWNER_UNAVAILABLE")
        return current

    return SourceChatService(auth, request.app.state.agent_service, refresh_auth)


@ChatRouter.get("/capabilities", summary="获取已启用的聊天能力", response_model=ResponseSchema[ChatCapabilitiesSchema])
async def chat_capabilities_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:query"]))],
) -> JSONResponse:
    source_available = False
    if settings.AI_CHAT_ENGINE == "deerflow_source":
        from app.modules.ai.agent.lifecycle import SOURCE_CHAT_INTEGRATION_READY

        source_available = SOURCE_CHAT_INTEGRATION_READY
    result = ChatCapabilitiesSchema(protocol_version=2 if source_available else 1, source_available=source_available)
    return SuccessResponse(data=result, msg="获取聊天能力成功")


@ChatRouter.get("/detail/{session_id}", summary="获取会话详情", response_model=ResponseSchema[ChatSessionOutSchema])
async def get_session_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:detail"]))],
    session_id: Annotated[str, Path(description="会话ID")],
    request: Request,
) -> JSONResponse:
    if settings.AI_CHAT_ENGINE == "deerflow_source":
        try:
            await _source_http_chat(request, auth, "module_ai:chat:detail").repair_history(session_id)
        except LookupError:
            from app.common.enums import RET

            raise CustomException(msg="会话不存在", code=RET.NOT_FOUND.code)
    service = _session_service(auth)
    result = await service.get_session(session_id=session_id)
    return SuccessResponse(data=result, msg="获取会话详情成功")


@ChatRouter.get("/list", summary="查询会话列表", response_model=ResponseSchema[PageResultSchema[ChatSessionOutSchema]])
async def get_session_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[ChatSessionQueryParam, Query()],
) -> JSONResponse:
    service = _session_service(auth)
    result_dict = await service.page(
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
        order_by=page.order_by,
    )
    return SuccessResponse(data=result_dict, msg="查询会话列表成功")


@ChatRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建会话", response_model=ResponseSchema[ChatSessionOutSchema])
async def create_session_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:create"]))],
    data: Annotated[ChatSessionCreateSchema, Body(description="会话创建参数")],
) -> JSONResponse:
    service = _session_service(auth)
    result = await service.create(data=data)
    return SuccessResponse(data=result, msg="创建会话成功")


@ChatRouter.put("/update/{session_id}", summary="更新会话", response_model=ResponseSchema[None])
async def update_session_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:update"]))],
    session_id: Annotated[str, Path(description="会话ID")],
    data: Annotated[ChatSessionUpdateSchema, Body(description="会话更新参数")],
) -> JSONResponse:
    service = _session_service(auth)
    await service.update(session_id=session_id, data=data)
    return SuccessResponse(data=None, msg="更新会话成功")


@ChatRouter.delete("/delete", summary="删除会话", response_model=ResponseSchema[None])
async def delete_session_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:delete"]))],
    session_ids: Annotated[list[str], Body(description="会话ID列表")],
) -> JSONResponse:
    service = _session_service(auth)
    await service.delete(session_ids=session_ids)
    return SuccessResponse(data=None, msg="删除会话成功")


@ChatRouter.post("/ai-chat", summary="AI 对话（非流式）", response_model=ResponseSchema[AiChatResponseSchema])
async def ai_chat_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:query"]))],
    redis: Annotated[Redis, Depends(redis_getter)],
    data: Annotated[AiChatRequestSchema, Body(description="对话请求")],
    request: Request,
) -> JSONResponse:
    # 与 WebSocket 流式一致：优先使用用户激活的模型配置
    model_config = await get_user_model_config(redis, auth.user.id)
    if settings.AI_CHAT_ENGINE == "deerflow_source":
        from app.common.enums import RET

        source = _source_http_chat(request, auth)
        sid = data.session_id
        if not sid:
            session = await SourceSessionService(auth).create(ChatSessionCreateSchema(title=data.message[:200]))
            sid = session.session_id
        response_parts: list[str] = []
        succeeded = False
        async with aclosing(source.stream(session_id=sid, turn_id=uuid.uuid4().hex, message=data.message, skills=None, model_config=model_config)) as events:
            async for event in events:
                if event.type == "text.delta" and isinstance(event.payload.get("text"), str):
                    response_parts.append(event.payload["text"])
                elif event.type == "turn.completed":
                    succeeded = True
                elif event.type in {"turn.failed", "turn.stopped"}:
                    raise CustomException(msg="AI 服务暂时不可用，请稍后重试", code=RET.SERVERERR.code)
        if not succeeded:
            raise CustomException(msg="AI 服务暂时不可用，请稍后重试", code=RET.SERVERERR.code)
        result = {"response": "".join(response_parts), "session_id": sid, "function_calls": None, "action": None}
    else:
        result = await ChatService(auth).chat_non_stream(message=data.message, session_id=data.session_id, model_config=model_config)
    return SuccessResponse(
        data=AiChatResponseSchema(
            response=result["response"],
            session_id=result["session_id"],
            function_calls=result.get("function_calls"),
            action=result.get("action"),
        ),
        msg="对话成功",
    )


@ChatRouter.get("/model", summary="获取 AI 模型配置列表", response_model=ResponseSchema[AiModelConfigListResponse])
async def list_model_config_controller(
    redis: Annotated[Redis, Depends(redis_getter)],
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:query"]))],
) -> JSONResponse:
    service = AiModelConfigService(auth, redis)
    result = await service.list_configs()
    return SuccessResponse(data=result, msg="获取模型配置列表成功")


@ChatRouter.post("/model", status_code=status.HTTP_201_CREATED, summary="新增一个 AI 模型配置", response_model=ResponseSchema[dict[str, Any]])
async def create_model_config_controller(
    redis: Annotated[Redis, Depends(redis_getter)],
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:update"]))],
    data: Annotated[AiModelConfigSchema, Body(description="模型配置参数")],
) -> JSONResponse:
    service = AiModelConfigService(auth, redis)
    result = await service.create(data)
    return SuccessResponse(data=result, msg="模型配置已新增")


@ChatRouter.put("/model/{config_id}", summary="更新指定 ID 的 AI 模型配置", response_model=ResponseSchema[dict[str, Any]])
async def update_model_config_controller(
    redis: Annotated[Redis, Depends(redis_getter)],
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:update"]))],
    config_id: Annotated[str, Path(description="配置项 ID")],
    data: Annotated[AiModelConfigSchema, Body(description="模型配置参数")],
) -> JSONResponse:
    service = AiModelConfigService(auth, redis)
    result = await service.update(config_id, data)
    return SuccessResponse(data=result, msg="模型配置已更新")


@ChatRouter.delete("/model/{config_id}", summary="删除指定 ID 的 AI 模型配置", response_model=ResponseSchema[None])
async def delete_model_config_controller(
    redis: Annotated[Redis, Depends(redis_getter)],
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:update"]))],
    config_id: Annotated[str, Path(description="配置项 ID")],
) -> JSONResponse:
    service = AiModelConfigService(auth, redis)
    await service.delete(config_id)
    return SuccessResponse(data=None, msg="模型配置已删除")


@ChatRouter.post("/model/{config_id}/activate", summary="切换激活的 AI 模型配置", response_model=ResponseSchema[None])
async def activate_model_config_controller(
    redis: Annotated[Redis, Depends(redis_getter)],
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:update"]))],
    config_id: Annotated[str, Path(description="配置项 ID；传 __default__ 使用系统默认")],
) -> JSONResponse:
    service = AiModelConfigService(auth, redis)
    await service.set_active(config_id)
    return SuccessResponse(data=None, msg="已切换模型")


@dataclass(slots=True)
class _LegacyTurn:
    """One connection-owned generation; a terminal frame clears it."""

    session_id: str | None
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    phase: str = "running"
    task: asyncio.Task[None] | None = None


@dataclass(slots=True)
class _SocketMessage:
    text: str
    turn: _LegacyTurn | None = None
    terminal: bool = False


def _cancel_once(task: asyncio.Task[Any] | None) -> None:
    # A second cancel can interrupt an async generator's resource cleanup.
    if task is not None and not task.done() and not task.cancelling():
        task.cancel()


async def _run_legacy_socket(websocket: WebSocket, auth: AuthSchema) -> None:
    """Receive, generate and send independently; retain the legacy wire format."""
    outgoing: asyncio.Queue[_SocketMessage] = asyncio.Queue(maxsize=32)
    active_turn: _LegacyTurn | None = None
    chat_service = ChatService(auth)
    redis = websocket.app.state.redis

    async def generate(turn: _LegacyTurn, query: ChatQuerySchema) -> None:
        try:
            model_config = await get_user_model_config(redis, auth.user.id)
            stream = chat_service.chat_query(query=query, stop_event=turn.stop_event, model_config=model_config)
            async with aclosing(stream):
                async for chunk in stream:
                    if chunk and turn.phase == "running":
                        await outgoing.put(_SocketMessage(chunk, turn))
        except asyncio.CancelledError:
            raise
        except CustomException as exc:
            turn.phase = "failed"
            await outgoing.put(_SocketMessage(f"错误: {exc.msg}", turn))
        except Exception:
            # Model and transport exceptions may contain private configuration.
            turn.phase = "failed"
            logger.error("WebSocket聊天生成失败")
            await outgoing.put(_SocketMessage("错误: AI 服务暂时不可用，请稍后重试", turn))
        else:
            turn.phase = "completed"
        await outgoing.put(_SocketMessage("[DONE]", turn, terminal=True))

    async def receive() -> None:
        nonlocal active_turn
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message_data = json.loads(data)
                    if not isinstance(message_data, dict):
                        raise ValueError("expected an object")
                    query = ChatQuerySchema(**message_data)
                except (ValueError, TypeError):
                    await outgoing.put(_SocketMessage("消息格式错误，请发送JSON格式的消息"))
                    continue

                if query.action == "stop":
                    turn = active_turn
                    if turn is None or turn.phase != "running" or (query.session_id is not None and query.session_id != turn.session_id):
                        await outgoing.put(_SocketMessage("当前没有正在进行的生成任务"))
                        continue
                    turn.phase = "stopping"
                    turn.stop_event.set()
                    _cancel_once(turn.task)
                    if turn.task is not None:
                        # Receiver cancellation on disconnect must not cancel
                        # the generation a second time during its cleanup.
                        await asyncio.shield(asyncio.gather(turn.task, return_exceptions=True))
                    turn.phase = "stopped"
                    await outgoing.put(_SocketMessage("[STOPPED]", turn, terminal=True))
                    continue

                if active_turn is not None:
                    await outgoing.put(_SocketMessage("当前有正在进行的生成任务，请稍后再试"))
                    continue
                turn = _LegacyTurn(session_id=query.session_id)
                active_turn = turn
                turn.task = asyncio.create_task(generate(turn, query))
        except WebSocketDisconnect:
            return

    async def send() -> None:
        nonlocal active_turn
        while True:
            item = await outgoing.get()
            if item.turn is not None and not item.terminal and item.turn.phase in {"stopping", "stopped"}:
                continue
            await websocket.send_text(item.text)
            if item.terminal and active_turn is item.turn:
                active_turn = None

    receiver = asyncio.create_task(receive())
    sender = asyncio.create_task(send())
    try:
        done, _ = await asyncio.wait((receiver, sender), return_when=asyncio.FIRST_COMPLETED)
        for completed in done:
            completed.result()
    finally:
        _cancel_once(receiver)
        _cancel_once(sender)
        if active_turn is not None:
            active_turn.stop_event.set()
            _cancel_once(active_turn.task)
        tasks = [receiver, sender]
        if active_turn is not None and active_turn.task is not None:
            tasks.append(active_turn.task)
        await asyncio.gather(*tasks, return_exceptions=True)


@ChatRouter.websocket("/ws", name="WebSocket聊天")
async def websocket_chat_controller(websocket: WebSocket) -> None:
    """WebSocket 聊天接口。

    支持的消息格式（JSON）：
    - 对话：{"message": "...", "session_id": "...", "files": [...]}
    - 停止：{"action": "stop", "session_id": "..."}

    ws://127.0.0.1:8001/api/v1/ai/chat/ws

    令牌优先通过 Sec-WebSocket-Protocol 携带（不会进入网关/服务的 access log）：
      new WebSocket(url, ["access_token", "access_token." + jwt])
    小程序等无法自定义子协议的客户端，可用 ?token= 兜底。
    """
    # 握手阶段完成认证；未 accept 前无法发送业务报文，失败直接关闭
    try:
        auth, subprotocol = await websocket_authenticate(websocket)
    except Exception as e:
        logger.warning("WebSocket认证失败: {}", e)
        await websocket.close(code=4001, reason="无效令牌")
        return

    # 权限校验：与 HTTP 对话端点一致，未授权用户拒绝握手
    if not _has_chat_permission(auth):
        logger.warning("WebSocket权限不足: 用户={}", auth.user.username)
        await websocket.close(code=4003, reason="无权限")
        return

    await websocket.accept(subprotocol=subprotocol)
    try:
        logger.info("WebSocket连接已建立: {} - 用户: {}", websocket.client, auth.user.username or "未认证")
        if settings.AI_CHAT_ENGINE == "deerflow_source":
            from .source_service import SourceChatService
            from .source_socket import run_source_socket

            async def refresh_auth() -> AuthSchema:
                current, _ = await websocket_authenticate(websocket)
                if current.user.id != auth.user.id or not _has_chat_permission(current):
                    raise PermissionError("CHAT_OWNER_UNAVAILABLE")
                return current

            service = SourceChatService(auth, websocket.app.state.agent_service, refresh_auth)
            await run_source_socket(websocket, auth, service, websocket.app.state.redis)
        else:
            await _run_legacy_socket(websocket, auth)
    except (RuntimeError, WebSocketDisconnect):
        logger.info("WebSocket连接已断开: {}", websocket.client)
    except Exception:
        logger.error("WebSocket服务异常")
        try:
            await websocket.close(code=1011)
        except RuntimeError:
            pass
