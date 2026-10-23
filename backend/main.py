import os
import sys
from typing import Annotated

import typer
import uvicorn
from alembic import command
from alembic.config import Config
from typer.main import Typer

from app.common.enums import EnvironmentEnum

fastapiadmin_cli: Typer = typer.Typer()
alembic_cfg: Config = Config(file_="alembic.ini")


@fastapiadmin_cli.command(
    name="run",
    help="启动 FastapiAdmin 服务, 运行 python(或uv run) main.py run --env=dev 不加参数默认 dev 环境",
)
def run(
    env: Annotated[EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")] = EnvironmentEnum.DEV,
) -> None:
    """按指定环境启动 Uvicorn；非 Windows 环境按 DEBUG 自动开启 reload。

    参数:
    - env (EnvironmentEnum): 运行环境，对应 `--env`。

    返回:
    - None
    """
    os.environ["ENVIRONMENT"] = env.value

    from app.config.setting import settings

    is_windows = sys.platform == "win32"
    # A shared listener cannot be registered with a new Windows IOCP after
    # reload/worker restart (WinError 87). Keep Proactor for Playwright, but
    # let the serving process create and own its listener.
    if is_windows and (settings.DEBUG or settings.WORKERS > 1):
        typer.echo("Windows 使用单进程 Proactor 模式，已关闭热重载和多 worker；修改代码后请手动重启服务。", err=True)

    uvicorn.run(
        app="app:create_app",
        factory=True,
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG and not is_windows,
        workers=1 if is_windows else settings.WORKERS,
        loop="app.core.server_loop:subprocess_event_loop" if is_windows else "auto",
        log_config=None,
        timeout_graceful_shutdown=5,
    )


@fastapiadmin_cli.command(
    name="revision",
    help="生成新的 Alembic 迁移脚本, 运行 python(或uv run) main.py revision --env=dev",
)
def revision(
    env: Annotated[EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")] = EnvironmentEnum.DEV,
    message: Annotated[str, typer.Option("--message", "-m", help="迁移说明（进入迁移文件名 slug）")] = "迁移脚本",
) -> None:
    """使用 Alembic 自动生成迁移脚本（autogenerate）。

    参数:
    - env (EnvironmentEnum): 运行环境，用于加载对应数据库模型元数据。
    - message (str): 迁移说明，写入迁移文件 message 与文件名 slug。

    返回:
    - None
    """
    os.environ["ENVIRONMENT"] = env.value
    command.revision(config=alembic_cfg, autogenerate=True, message=message)
    typer.echo(message="迁移脚本已生成")


@fastapiadmin_cli.command(
    name="upgrade",
    help="应用最新的 Alembic 迁移, 运行 python(或uv run) main.py upgrade --env=dev",
)
def upgrade(
    env: Annotated[EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")] = EnvironmentEnum.DEV,
) -> None:
    """将数据库升级到 Alembic 最新版本（head）。

    参数:
    - env (EnvironmentEnum): 运行环境。

    返回:
    - None
    """
    os.environ["ENVIRONMENT"] = env.value
    command.upgrade(config=alembic_cfg, revision="head")
    typer.echo(message="所有迁移已应用。")


if __name__ == "__main__":
    fastapiadmin_cli()
