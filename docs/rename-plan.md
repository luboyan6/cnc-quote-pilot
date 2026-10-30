# 项目改名方案（逐文件清单 + 命令）

> 状态：**待执行**。名字确定后，把下面三个派生值填上，命令即可直接跑。
> 生成时间：2026-10-29 · 基于当前工作区实测（125 个命中文件）

## 0. 先填三个派生值

```bash
NAME=keel          # 小写：仓库名 / 包名 / 前缀（如 keel）
TITLE=Keel         # 展示名：首字母大写（如 Keel）
CN=龙骨             # 中文名，可选（如 龙骨）
```

命名体系约定：

| 层级 | 形态 | 示例 |
|---|---|---|
| 基座仓库 | `NAME` | `keel` |
| 业务分支 / 产品 | `NAME-<行业>-<场景>` | `keel-cnc-quote` |
| Python 包 | 保持 `app`（不改） | `app` |
| 数据库表前缀 | 保持 `sys_` / `platform_` / `task_` / `gen_`（不改） | — |

---

## 1. 现状盘点

排除 `node_modules` / `dist` / `.git` / `__pycache__` / `scratch` / `.trellis` / `logs` / `.venv` / `*.log` 后，命中 `fastapiadmin` 的文件 **125 个**：

| 区域 | 文件数 | 说明 |
|---|---|---|
| `frontend/web` | 38 | 包名、console banner、常量链接、i18n |
| `frontend/docs` | 29 | VitePress 文档站（上游文档，可选是否维护） |
| `backend` | 20 | 配置、日志、CLI、banner、种子数据、测试断言 |
| `frontend/app` | 13 | 小程序 `.env`、i18n |
| `docker` | 7 | compose、nginx、`.env.example` |
| 根目录文档 | 13 | README / LICENSE / CHANGELOG / 需求 / 设计稿 |
| 脚本 + docs | 4 | `deploy.sh` / `deploy-artifacts.sh` / `docs/*.md` |
| 历史审计报告 | 2 | `audit-*.md`、`AUDIT-REPORT.md`（**不改**） |

### 三个"零成本"的好消息

1. **没有 import 路径要改**：Python 包目录本来就是 `app/`，不叫 `fastapiadmin/`。
2. **前端存储键已是中性**：`STORAGE_PREFIX = "sys-v"`（`frontend/web/src/utils/storage/index.ts:42`），改名不影响用户本地缓存。
3. **表前缀全中性**：`sys_` / `platform_` / `task_` / `gen_` / `example_`，**不需要任何数据库迁移**。

---

## 2. 三层执行顺序（每层一个独立 commit，可单独回滚）

### L1 · 品牌层（安全，先做）

| 文件 | 改什么 |
|---|---|
| `README.md` / `README.en.md` | 标题、副标题、`git clone` URL、目录树里的 `FastapiAdmin/`、徽章链接 |
| `backend/pyproject.toml` | `name`、`description` |
| `frontend/web/package.json` | `name`、`description`、`repository`、`author`、`homepage` |
| `frontend/web/src/utils/sys/index.ts` | console banner ASCII art + 社区链接 |
| `backend/app/utils/banner.py` | 启动 ASCII banner |
| `backend/app/utils/console.py:96,116` | 启动/关闭标题 `🚀 FastapiAdmin v…` |
| `backend/app/config/setting.py:42` | `TITLE`（Swagger 文档标题） |
| `backend/app/__init__.py:1` | 模块 docstring |
| `frontend/app/.env.development` / `.env.production` | `VITE_APP_TITLE` |
| `docker/.env.example:69` | `PROJECT_NAME` |
| `SKILL.md` | frontmatter `name:` + 正文标题 |
| `CHANGELOG.md` / `REQUIREMENTS.md` / `CONTRIBUTING.md` / `DEPLOYMENT.md` / `TEAM-PLAYBOOK.md` / `CNC_…_SRS_Design_v1.0.md` | 正文品牌词 |

### L2 · 部署层（中风险，需重建验证）

| 文件 | 改什么 | 注意 |
|---|---|---|
| `docker/.env.example:9,10` | `MYSQL_DATABASE` / `MYSQL_USER` | 只对**新建库**生效；已有库改了会连不上 |
| `backend/env/.env.example:35` | `DATABASE_NAME` | 同上 |
| `backend/app/config/setting.py:112` | `DATABASE_NAME` 默认值 | 同上 |
| `deploy.sh` / `deploy-artifacts.sh` | 容器名、镜像名、远端部署目录 | 已部署服务器上的旧容器需手动清理 |
| `docker/nginx/nginx.conf:2` | 文件头注释 | — |
| `docker/README.md`、`docker/audit-deploy.md` | 文档 | 审计报告建议**不改**（见 §4） |

### L3 · 代码标识（高风险，单独一次提交 + 回归）

| 位置 | 现值 | 改的后果 | 建议 |
|---|---|---|---|
| `backend/app/utils/crypto_util.py:23` | `b"fastapiadmin:data-encryption:v1"` | 🚫 **存量密文全部解不开**（KDF info 参数） | **禁止修改** |
| `backend/app/config/setting.py:69` | `SECRET_KEY` 默认值 | 改 = 所有 JWT 立即失效，全员重登 | 可改，但要挑低峰期 |
| `backend/app/core/ap_scheduler.py:65` | `fastapiadmin:scheduler:lock` | 滚动发布期新旧实例锁不互斥 → 定时任务双跑 | 停服改，或保留 |
| `backend/app/core/sse_manager.py:100` | `fastapiadmin:sse:{channel}` | 滚动发布期跨实例 SSE 消息丢失 | 停服改，或保留 |
| `backend/app/core/logger.py:59` | `fastapiadmin.log` | 旧日志不再写入；`SKILL.md` 第 8 节的排障路径要同步 | 可改 |
| `backend/main.py:13,17,56,78,99` | `fastapiadmin_cli` | 纯内部符号，无外部依赖 | 可改 |
| `backend/app/utils/ai_factory.py:57-91` | `fastapiadmin_agent` / `fastapiadmin_team` | Agno Agent/Team 名称 | 可改 |
| `backend/sql/sys_param.json` | logo/favicon/背景/版权/帮助文档/隐私条款 URL + `FastapiAdmin系统` | **种子数据**，只影响新库 | 改后老库需 `UPDATE sys_param` |
| `backend/sql/sys_user.json` | 种子用户邮箱等 | 只影响新库 | 按需 |
| `backend/tests/test_security_defaults.py:457,464` | 断言硬编码 `service.fastapiadmin.com` | 改 `setting.py` 的域名必须同步改断言 | 与 L2 一起改 |

---

## 3. 执行命令

```bash
# 1) 生成目标清单（排除产物 / 日志 / 历史审计报告）
grep -rIil \
  --exclude-dir={node_modules,dist,.git,__pycache__,scratch,.trellis,.playwright-mcp,logs,.venv} \
  --exclude="*.log" --exclude="audit-*.md" --exclude="AUDIT-REPORT.md" \
  "fastapiadmin" . > /tmp/targets.txt

# 2) 剔除禁止改名的文件
cat > /tmp/keep.txt <<'EOF'
./backend/app/utils/crypto_util.py
./frontend/web/src/utils/constants/definitions.ts
./LICENSE
EOF
grep -v -F -f /tmp/keep.txt /tmp/targets.txt > /tmp/safe.txt

# 3) 批量替换（先长后短，避免 FastapiAdmin 被拆成子串）
perl -pi -e "s/FastapiAdmin/$TITLE/g; s/fastapiadmin/$NAME/g" $(cat /tmp/safe.txt)

# 4) 核对：应显示约 120 个文件改动，且无残留
git diff --stat | tail -3
grep -rn -i "fastapiadmin" $(cat /tmp/safe.txt) | head
```

> 无 `perl` 时用 `sed -i`，但 sed 需分两次执行（先 `FastapiAdmin` 后 `fastapiadmin`）。

L3 的每一处**不要走批量替换**，按上表逐条手改并单独提交。

---

## 4. 明确不改的清单

| 项 | 原因 |
|---|---|
| `backend/audit-*.md`、`frontend/audit-*.md`、`docker/audit-deploy.md` | 历史审计报告，改写即失真；需要时在文首加一行「品牌已迁移至 X」即可 |
| `LICENSE` 中的原始版权行 | MIT 协议要求保留原作者版权声明，只能在文件尾部追加 fork 说明 |
| `frontend/web/src/utils/constants/definitions.ts` 的上游链接 | 标明派生来源，便于日后跟进上游更新；确定脱钩后再改 |
| `backend/app/utils/crypto_util.py:23` | 改了会毁掉存量加密数据 |
| `service.fastapiadmin.com` 这类**域名** | 这是上游官方域名，与品牌改名是两件事，见 §5 |
| `.playwright-mcp/*.log`、`backend/logs/*.log`、`backend/.venv/**` | 临时产物 / 虚拟环境，直接忽略 |

---

## 5. 顺手修一个已知隐患（可选）

`docker/audit-deploy.md` 的 **M14** 已记录：`ALLOWED_HOSTS` 与 `nginx.conf` 的 `server_name` 硬编码了 `service.fastapiadmin.com`，**换域名即全站 400**。

既然要改名，建议同一次把这两处改成读环境变量（`ALLOWED_HOSTS` / `NGINX_SERVER_NAME`），而不是把硬编码值换成另一个硬编码值。

涉及：
- `backend/app/config/setting.py:160,195`
- `docker/nginx/nginx.conf:75,94`
- `docker/.env.example:43,56`
- `backend/tests/test_security_defaults.py:457,464`（断言改为读环境变量后校验）

---

## 6. 验证清单

```bash
# 品牌残留（应只剩 §4 白名单）
grep -rn -i "fastapiadmin" --exclude-dir={node_modules,dist,.git,.venv,logs,scratch} . | grep -v "crypto_util\|definitions.ts\|LICENSE\|audit-" 

# 后端
cd backend && uv run pytest -q

# 前端
cd frontend/web && pnpm ts:check && pnpm build

# 部署
docker compose -f docker/docker-compose.yaml config > /dev/null && echo OK
```

启动后人工确认四项：① 控制台 banner ② `backend/logs/<NAME>.log` 生成 ③ Swagger 标题 ④ 登录页版权文案。

---

## 7. 仓库层改名

1. GitHub → Settings → Rename repository（旧 URL 自动 301 跳转，不破坏已有克隆）
2. 本地：`git remote set-url origin https://github.com/luboyan6/<NAME>.git`
3. 本地目录改名：`cnc-quote-pilot` → `<NAME>`
4. 检查 CI / 部署脚本 / 服务器上的 `cd /home/FastapiAdmin` 类硬编码路径
5. 当前分支 `feat/deerflow-cnc-lead-agent` 保留不动；CNC 业务代码留在该分支，作为 `NAME` 基座的第一个派生项目
