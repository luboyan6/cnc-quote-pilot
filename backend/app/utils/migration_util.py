"""自动迁移的兼容性与数据保留规则。"""

import ast
import re

from alembic.operations import MigrationScript, ops
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Identity, Integer, MetaData


def preserve_postgresql_identity(context: MigrationContext, script: MigrationScript, metadata: MetaData) -> int:
    """通用自增主键未声明 Identity 时，保留数据库已有的 PostgreSQL IDENTITY。

    生成模型继承 ModelMixin.id；autoincrement=True 并不要求数据库从 IDENTITY
    改成 SERIAL。显式 Identity 选项或其他 server_default 的变更仍交给 Alembic。
    只处理自动生成的操作树，不修改 metadata，也不干预手写迁移的执行。
    """
    if context.dialect.name != "postgresql":
        return 0

    preserved: set[tuple[str | None, str, str]] = set()

    def prune(container: ops.OpContainer, *, downgrade: bool = False) -> None:
        remaining: list[ops.MigrateOperation] = []
        for operation in container.ops:
            if isinstance(operation, ops.ModifyTableOps):
                prune(operation, downgrade=downgrade)
                if not operation.is_empty():
                    remaining.append(operation)
                continue

            if isinstance(operation, ops.AlterColumnOp):
                key = (operation.schema, operation.table_name, operation.column_name)
                if downgrade:
                    if key in preserved and isinstance(operation.modify_server_default, Identity):
                        operation.modify_server_default = False
                elif isinstance(operation.existing_server_default, Identity) and operation.modify_server_default is None:
                    table_key = f"{operation.schema}.{operation.table_name}" if operation.schema else operation.table_name
                    table = metadata.tables.get(table_key)
                    column = table.c.get(operation.column_name) if table is not None else None
                    if column is not None and column.primary_key and isinstance(column.type, Integer) and column.autoincrement in (True, "auto") and column.server_default is None:
                        operation.modify_server_default = False
                        preserved.add(key)

                if not operation.has_changes():
                    continue

            remaining.append(operation)
        container.ops = remaining

    for upgrade in script.upgrade_ops_list:
        prune(upgrade)
    for downgrade in script.downgrade_ops_list:
        prune(downgrade, downgrade=True)
    return len(preserved)


def has_destructive_upgrade(content: str) -> bool:
    """识别 upgrade 中直接或 batch 调用的 DROP；downgrade 的回滚操作不参与。"""
    tree = ast.parse(content)
    for function in tree.body:
        if not isinstance(function, ast.FunctionDef) or function.name != "upgrade":
            continue
        receivers = {"op"}
        for node in ast.walk(function):
            if isinstance(node, ast.withitem) and isinstance(node.context_expr, ast.Call):
                call = node.context_expr.func
                if isinstance(call, ast.Attribute) and call.attr == "batch_alter_table" and isinstance(node.optional_vars, ast.Name):
                    receivers.add(node.optional_vars.id)
        for node in ast.walk(function):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            receiver = node.func.value
            if not isinstance(receiver, ast.Name) or receiver.id not in receivers:
                continue
            if node.func.attr.startswith("drop_"):
                return True
            if node.func.attr == "execute" and node.args:
                sql = node.args[0]
                if isinstance(sql, ast.Constant) and isinstance(sql.value, str) and re.search(r"\bDROP\b", sql.value, re.IGNORECASE):
                    return True
    return False
