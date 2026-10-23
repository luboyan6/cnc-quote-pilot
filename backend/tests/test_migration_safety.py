"""生成模型与 PostgreSQL IDENTITY 兼容，以及自动迁移的 DROP 守卫。"""

from io import StringIO
from textwrap import dedent

import pytest
from alembic.autogenerate import render_python_code
from alembic.operations import MigrationScript, Operations, ops
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Column, Identity, Integer, MetaData, Table

from app.utils.migration_util import has_destructive_upgrade, preserve_postgresql_identity


def _identity_diff(*, schema: str | None = None, **changes) -> MigrationScript:
    alter = ops.AlterColumnOp(
        "generated_platform",
        "id",
        schema=schema,
        existing_type=Integer(),
        existing_server_default=Identity(),
        modify_server_default=None,
        **changes,
    )
    upgrade = ops.UpgradeOps([ops.ModifyTableOps("generated_platform", [alter], schema=schema)])
    return MigrationScript(None, upgrade, upgrade.reverse())


@pytest.mark.parametrize("schema", [None, "custom_schema"])
def test_inherited_autoincrement_preserves_database_identity(schema: str | None) -> None:
    metadata = MetaData()
    table = Table("generated_platform", metadata, Column("id", Integer, primary_key=True, autoincrement=True), schema=schema)
    script = _identity_diff(schema=schema)
    context = MigrationContext.configure(dialect_name="postgresql")

    assert preserve_postgresql_identity(context, script, metadata) == 1
    assert script.upgrade_ops.is_empty()
    assert script.downgrade_ops.is_empty()
    assert table.c.id.identity is None  # 不能把反射状态写回共享模型。


def test_identity_filter_keeps_other_column_changes_in_both_directions() -> None:
    metadata = MetaData()
    Table("generated_platform", metadata, Column("id", Integer, primary_key=True))
    script = _identity_diff(existing_comment="旧注释", modify_comment="新注释")
    context = MigrationContext.configure(dialect_name="postgresql")

    preserve_postgresql_identity(context, script, metadata)
    upgrade = render_python_code(script.upgrade_ops, migration_context=context)
    downgrade = render_python_code(script.downgrade_ops, migration_context=context)
    assert "新注释" in upgrade
    assert "旧注释" in downgrade
    sql = StringIO()
    executor = Operations(MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": sql}))
    executor.invoke(script.upgrade_ops.ops[0].ops[0])
    executor.invoke(script.downgrade_ops.ops[0].ops[0])
    assert "COMMENT ON COLUMN" in sql.getvalue()
    assert "DROP DEFAULT" not in sql.getvalue()
    assert "DROP IDENTITY" not in sql.getvalue()


@pytest.mark.parametrize(
    "dialect, column",
    [
        ("mysql", Column("id", Integer, primary_key=True)),
        ("postgresql", Column("id", Integer, primary_key=True, autoincrement=False)),
        ("postgresql", Column("id", Integer, primary_key=True, server_default="42")),
        ("postgresql", Column("id", Integer)),
    ],
)
def test_identity_filter_does_not_hide_other_default_changes(dialect: str, column: Column) -> None:
    metadata = MetaData()
    Table("generated_platform", metadata, column)
    script = _identity_diff()

    assert preserve_postgresql_identity(MigrationContext.configure(dialect_name=dialect), script, metadata) == 0
    assert not script.upgrade_ops.is_empty()


def test_explicit_identity_option_changes_remain_migratable() -> None:
    metadata = MetaData()
    Table("generated_platform", metadata, Column("id", Integer, Identity(always=True), primary_key=True))
    script = _identity_diff()
    script.upgrade_ops.ops[0].ops[0].modify_server_default = Identity(always=True)

    assert preserve_postgresql_identity(MigrationContext.configure(dialect_name="postgresql"), script, metadata) == 0
    assert "always=True" in render_python_code(script.upgrade_ops)


@pytest.mark.parametrize(
    "body",
    [
        "op.drop_table('accounts')",
        "op.drop_column('accounts', 'password')",
        "with op.batch_alter_table('accounts') as batch_op:\n    batch_op.drop_column('password')",
        "with op.batch_alter_table('accounts') as changes:\n    changes.drop_index('ix_accounts_id')",
        "op.execute(\n    'DROP TABLE accounts'\n)",
        "op.execute('drop table accounts')",
    ],
)
def test_drop_guard_covers_direct_and_batch_operations(body: str) -> None:
    source = "def upgrade():\n" + "\n".join("    " + line for line in body.splitlines())
    assert has_destructive_upgrade(source)


def test_drop_guard_allows_additions_and_downgrade_drops() -> None:
    assert not has_destructive_upgrade(
        dedent("""
        def upgrade():
            with op.batch_alter_table('platform') as batch_op:
                batch_op.add_column(sa.Column('uuid', sa.String(64)))

        def downgrade():
            op.drop_column('platform', 'uuid')
    """)
    )


def test_batch_drop_revision_is_rejected_before_auto_upgrade(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from alembic import command

    from app.scripts import initialize

    revision = tmp_path / "generated.py"

    def generate(*args, **kwargs) -> None:
        revision.write_text(
            dedent("""
            def upgrade():
                with op.batch_alter_table('accounts') as batch_op:
                    batch_op.drop_column('password')
        """),
            encoding="utf-8",
        )

    monkeypatch.setattr(initialize, "ALEMBIC_VERSION_DIR", tmp_path)
    monkeypatch.setattr(command, "revision", generate)
    assert initialize.InitializeData._InitializeData__autogen_migration(None) is None
    assert not revision.exists()
