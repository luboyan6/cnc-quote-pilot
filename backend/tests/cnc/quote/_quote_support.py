"""Isolated fixtures: real local transactions, synthetic browser/provider only."""

import asyncio
import logging
import sys
import tempfile
import unittest
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String, Table
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.base_schema import AuthSchema, CoreUserSchema
from app.modules.cnc.browser.errors import BrowserStop, Reason
from app.modules.cnc.login.contracts import AccountSnapshot
from app.modules.cnc.login.runtime import LoginManager
from app.modules.cnc.quote import authorization, repository
from app.plugin.module_cnc.cnc_quote.model import CncQuoteIntentModel as IntentDeclaration
from app.plugin.module_cnc.cnc_quote.model import CncQuoteRunModel as RunDeclaration

STEP = b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;"


class Base(DeclarativeBase):
    pass


# Use the exact production tables/constraints in an independent ORM registry.
# The app registry includes unrelated UserMixin relations and is deliberately
# not configured by these transaction tests or connected to a business DB.
class CncQuoteRunModel(Base):
    __table__ = RunDeclaration.__table__.to_metadata(Base.metadata)


class CncQuoteIntentModel(Base):
    __table__ = IntentDeclaration.__table__.to_metadata(Base.metadata)


USER_ROLES = Table("isolated_user_roles", Base.metadata, Column("user_id", ForeignKey("isolated_user.id"), primary_key=True), Column("role_id", ForeignKey("isolated_role.id"), primary_key=True))
ROLE_MENUS = Table("isolated_role_menus", Base.metadata, Column("role_id", ForeignKey("isolated_role.id"), primary_key=True), Column("menu_id", ForeignKey("isolated_menu.id"), primary_key=True))


class User(Base):
    __tablename__ = "isolated_user"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(default="synthetic")
    is_deleted: Mapped[bool] = mapped_column(default=False)
    status: Mapped[int] = mapped_column(default=0)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    roles: Mapped[list["Role"]] = relationship(secondary=USER_ROLES)


class Role(Base):
    __tablename__ = "isolated_role"
    id: Mapped[int] = mapped_column(primary_key=True)
    is_deleted: Mapped[bool] = mapped_column(default=False)
    status: Mapped[int] = mapped_column(default=0)
    menus: Mapped[list["Menu"]] = relationship(secondary=ROLE_MENUS)


class Menu(Base):
    __tablename__ = "isolated_menu"
    id: Mapped[int] = mapped_column(primary_key=True)
    is_deleted: Mapped[bool] = mapped_column(default=False)
    status: Mapped[int] = mapped_column(default=0)
    permission: Mapped[str] = mapped_column(String(100))


class Config(Base):
    __tablename__ = "isolated_config"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_id: Mapped[int] = mapped_column(default=7)
    is_deleted: Mapped[bool] = mapped_column(default=False)
    enabled: Mapped[bool] = mapped_column(default=True)
    site_type: Mapped[int] = mapped_column(default=48)
    part_id: Mapped[int] = mapped_column(default=9)
    material: Mapped[str] = mapped_column(default="Aluminum 6061")
    quantity: Mapped[int] = mapped_column(default=2)
    surface_finish: Mapped[str | None] = mapped_column(default=None)
    extra_params: Mapped[dict] = mapped_column(JSON, default=dict)


class Part(Base):
    __tablename__ = "isolated_part"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_id: Mapped[int] = mapped_column(default=7)
    is_deleted: Mapped[bool] = mapped_column(default=False)
    extension: Mapped[str] = mapped_column(default="step")
    file_path: Mapped[str] = mapped_column()
    file_name: Mapped[str] = mapped_column(default="synthetic.step")
    size_bytes: Mapped[int] = mapped_column(default=len(STEP))
    declared_unit: Mapped[str] = mapped_column(default="mm")
    validation_status: Mapped[str] = mapped_column(default="HEADER_VALID")
    upload_authorized: Mapped[bool] = mapped_column(default=True)


class Platform(Base):
    __tablename__ = "isolated_platform"
    id: Mapped[int] = mapped_column(primary_key=True)
    is_deleted: Mapped[bool] = mapped_column(default=False)
    login_url: Mapped[str] = mapped_column(default="https://www.xometry.com/account/login/")
    quote_entry_url: Mapped[str] = mapped_column(default="https://www.xometry.com/quoting/home/")


class Account(Base):
    __tablename__ = "isolated_account"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_id: Mapped[int] = mapped_column(default=7)
    platform_id: Mapped[int] = mapped_column(default=48)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    alias: Mapped[str] = mapped_column(String, default="Synthetic")
    username: Mapped[str] = mapped_column(String, default="synthetic@example.test")
    lease_owner: Mapped[str | None] = mapped_column(nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


ACCOUNT = AccountSnapshot(31, 7, 7, 48, "Synthetic", "synthetic@example.test", "synthetic-password", "PASSWORD", "https://www.xometry.com/account/login/", "https://www.xometry.com/quoting/home/", "account-rev", None)


class QuoteDatabase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.previous_log_level = logging.getLogger("aiosqlite").level
        logging.getLogger("aiosqlite").setLevel(logging.WARNING)
        self.temp = tempfile.TemporaryDirectory(prefix="cnc-quote-test-")
        self.root = Path(self.temp.name)
        self.file = self.root / "synthetic.step"
        self.file.write_bytes(STEP)
        self.engine = create_async_engine("sqlite+aiosqlite:///" + str(self.root / "test.db"), hide_parameters=True)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db, db.begin():
            db.add_all([Config(id=5), Part(id=9, file_path=str(self.file)), Platform(id=48), Account(id=31)])
            role = Role(id=1, menus=[Menu(id=index, permission=value) for index, value in enumerate(["module_cnc:cnc_part_config:query", "module_cnc:cnc_part_config:update", "module_cnc:cnc_account:query", "module_cnc:cnc_account:update"], start=1)])
            db.add_all([User(id=7, roles=[role]), User(id=99, roles=[role])])
        self.patches = [patch.object(repository, name, model) for name, model in [("CncPartConfigModel", Config), ("CncPartModel", Part), ("CncPlatformModel", Platform), ("CncAccountModel", Account), ("CncQuoteRunModel", CncQuoteRunModel), ("CncQuoteIntentModel", CncQuoteIntentModel)]]
        self.patches.extend([patch.object(authorization, name, model) for name, model in [("UserModel", User), ("RoleModel", Role), ("MenuModel", Menu)]])
        for item in self.patches:
            item.start()
        self.login = SimpleNamespace(load=AsyncMock(return_value=ACCOUNT))
        self.repo = repository.QuoteRepository(self.sessions, self.login, self.root)
        self.auth = AuthSchema(user=CoreUserSchema(id=7, is_superuser=False))

    async def asyncTearDown(self):
        for item in reversed(self.patches):
            item.stop()
        await self.engine.dispose()
        self.temp.cleanup()
        logging.getLogger("aiosqlite").setLevel(self.previous_log_level)


class BrowserRepository:
    def __init__(self):
        self.claims = 0
        self.releases = []
        self.lost = False

    async def claim(self, account, owner):
        self.claims += 1
        return self.claims

    async def renew(self, *args, **kwargs):
        if self.lost:
            from app.modules.cnc.login.contracts import LoginError

            raise LoginError("ACCOUNT_CHANGED_OR_LEASE_LOST")

    async def release(self, *args):
        self.releases.append(args)


class BrowserExecutor:
    def __init__(self):
        self.active = 0
        self.navigation = []
        self.page = None
        self.cleanup_gate = None
        self.cleanup_entered = False

    @asynccontextmanager
    async def session(self, scope, policy, encrypted_state=None):
        owner = asyncio.current_task()
        self.active += 1

        def check():
            if asyncio.current_task() is not owner:
                raise BrowserStop(Reason.WRONG_CONSUMER)

        async def goto(url):
            check()
            self.navigation.append(url)

        page = SimpleNamespace(
            set_viewport_size=AsyncMock(), on=lambda *args: None,
            screenshot=AsyncMock(return_value=b"\xff\xd8synthetic\xff\xd9"),
            mouse=SimpleNamespace(click=AsyncMock(), wheel=AsyncMock()),
            keyboard=SimpleNamespace(press=AsyncMock(), insert_text=AsyncMock()),
        )
        self.page = page
        session = SimpleNamespace(scope=scope, check_active=check, invalidate_authentication=check, confirm_authentication=lambda auth: check(), page=page, goto=goto, export_encrypted_state=AsyncMock(return_value="encrypted-synthetic-state"))
        try:
            yield session
        finally:
            try:
                if self.cleanup_gate is not None:
                    self.cleanup_entered = True
                    await self.cleanup_gate.wait()
            finally:
                self.active -= 1


def browser_manager():
    repository = BrowserRepository()
    executor = BrowserExecutor()
    provider = SimpleNamespace(code="xometry_us", policy=None, verify=AsyncMock(return_value=True), submit=AsyncMock(return_value=True))
    manager = LoginManager(repository, executor, provider_resolver=lambda *args: provider)
    return manager, repository, executor, provider


async def wait_for(predicate, *, seconds=10):
    async with asyncio.timeout(seconds):
        while not predicate():
            await asyncio.sleep(0.01)
