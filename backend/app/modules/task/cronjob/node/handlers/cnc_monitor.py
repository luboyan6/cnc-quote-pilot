"""CNC 监测计划定时扫描处理器。

供 APScheduler 节点执行函数调用：func = "builtin:cnc_monitor.scan_due"
仅执行短数据库扫描与轮次/批次准入事务，实际报价由 Dispatcher 异步推进。
"""

import asyncio
from typing import Any

from app.core.logger import logger
from app.modules.cnc.monitor.service import get_monitor_service


async def scan_due_async() -> dict[str, Any]:
    """Run on the scheduler's event loop, sharing the async database pool."""
    results = await get_monitor_service().scan_due()
    return {"status": "ok", "dispatched_count": len(results), "results": results}


def scan_due(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """扫描所有到期的 CNC 监测计划并生成对应轮次与持久批次。

    返回:
    - dict: 包含执行状态与派发批次摘要。
    """
    try:
        from app.core.ap_scheduler import scheduler

        loop = getattr(scheduler, "_eventloop", None)
        if loop is not None and loop.is_running():
            # Builtin node handlers run in a scheduler worker thread. Use the
            # application loop so pooled async DB connections stay on one loop.
            future = asyncio.run_coroutine_threadsafe(scan_due_async(), loop)
            try:
                return future.result(timeout=55)
            except BaseException:
                future.cancel()
                raise
        return asyncio.run(scan_due_async())
    except Exception as exc:
        logger.error(f"CNC 监测计划定时扫描异常: {exc}", exc_info=True)
        return {
            "status": "error",
            "error": str(exc),
        }
