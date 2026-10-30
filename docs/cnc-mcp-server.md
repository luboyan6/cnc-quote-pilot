# CNC MCP Server

The backend exposes CNC account/drawing queries, controlled platform login, and an independent account-password decryption tool to external MCP clients through stateless Streamable HTTP. It runs inside FastAPI with the official Python MCP SDK and the application's current authentication and permissions. This feature implements MCP Server functionality only; it adds no outbound MCP client.

For the source analysis behind this design, see [WeKnora MCP Server analysis](./weknora-mcp-analysis.md).

## Connect another project to this development instance

The current local development environment uses `backend/env/.env.dev`, PostgreSQL, `SERVER_HOST=localhost`, and `SERVER_PORT=10006`. MCP is enabled in that local environment file. The application default and the checked-in environment template remain disabled. Restart the backend after changing the environment; an existing process does not reload this setting on Windows.

1. Start PostgreSQL and Redis using this project's existing configuration. From the repository root, start the backend:

   ```powershell
   Set-Location E:/AIWorkspace/cnc-quote-pilot/backend
   ./.venv/Scripts/python.exe main.py run --env=dev
   ```

   Stop an existing backend in its own terminal with `Ctrl+C` before starting its replacement. If the environment is not installed yet, run `uv sync --extra postgres` first. An operating-system `MCP_ENABLED` variable overrides the environment file; remove a stale override or set it to `true` in the launch environment.

2. For another project running directly on the same computer, use:

   ```text
   http://127.0.0.1:10006/api/v1/mcp/
   ```

   The direct backend URL `http://127.0.0.1:10006/mcp/` also works. Keep the trailing slash. The port `8001` used in the general examples below is the application default, not this local development override. A project inside a container or on another computer needs a reachable address as described below.

3. Sign in to the existing web application with an application user who can query CNC accounts and drawings. Open the browser's developer tools, select **Network**, and inspect a normal authenticated API request. Copy the token from `Authorization: Bearer ...`. Alternatively, inspect the response from `/api/v1/system/auth/login` and copy `data.access_token`.

   The front end stores the token as `access_token` in **Application > Local Storage** when Remember Me is selected, or **Session Storage** otherwise. Use the storage for the actual web application's origin. Use the application login token, not a vendor account password, vendor browser session, or `refresh_token`.

4. In the consuming project's MCP settings, add a **remote Streamable HTTP** server. Supply the URL above and a custom `Authorization` header with value `Bearer <access_token>`. If the client offers OAuth or manual Bearer/header authentication, choose manual Bearer/header authentication. A client that supports only stdio or requires OAuth cannot connect directly to this endpoint.

   For clients supporting the `mcpServers` URL/header format, copy [the connection template](./cnc-mcp-connection.example.json) into that client's configuration and replace the placeholder locally. Client-specific key names can differ; use the remote HTTP form documented by that client. Store the real token in its secret configuration, outside shared source control.

5. Reconnect or refresh the consuming project's tool list. With query/detail permissions and account update permission granted, the six tools are `cnc_account_list`, `cnc_account_detail`, `cnc_account_login`, `cnc_account_decrypt_password`, `cnc_part_list`, and `cnc_part_detail`. Test `cnc_part_list` with `{"page_no":1,"page_size":10}`. A valid empty `items` result is successful; `isError: true` is a tool failure even if the HTTP request returned 200.

There is no separate link-export or endpoint-token issuance screen. The connection consists of the endpoint URL, Streamable HTTP transport, and the caller's Authorization header. Share the URL and a placeholder configuration; give each caller an appropriate application identity and supply its token separately. The URL itself does not authorize queries.

### Verify discovery from PowerShell 7

After starting the backend and obtaining an access token, run this in PowerShell 7 on the same computer. The prompt masks input and the code prints tool names only:

```powershell
$mcpUrl = 'http://127.0.0.1:10006/api/v1/mcp/'
$mcpToken = Read-Host 'Paste the application access_token' -MaskInput
$mcpHeaders = @{
    Authorization = "Bearer $mcpToken"
    Accept = 'application/json, text/event-stream'
    'MCP-Protocol-Version' = '2025-11-25'
}
$mcpBody = @{
    jsonrpc = '2.0'
    id = 1
    method = 'tools/list'
    params = @{}
} | ConvertTo-Json -Depth 5
try {
    $mcpResult = Invoke-RestMethod -Method Post -Uri $mcpUrl `
        -Headers $mcpHeaders -ContentType 'application/json' -Body $mcpBody
    if ($mcpResult.error) {
        throw "MCP discovery failed: $($mcpResult.error.message)"
    }
    $mcpResult.result.tools | Select-Object -ExpandProperty name
} finally {
    Remove-Variable mcpToken, mcpHeaders
}
```

This is a direct discovery smoke check supported by this stateless server. A normal MCP client handles initialization and protocol negotiation itself. An HTTP 401 without a token proves only that an authenticated endpoint answered; it does not validate query access.

### Connect from another computer, container, or hosted project

`127.0.0.1` always addresses the caller's own host or container. For another computer to connect directly to this backend, configure a reachable server interface and its exact Host in the environment used by that deployment. For example, replace `192.168.1.50` with this computer's actual LAN IP:

```dotenv
SERVER_HOST=0.0.0.0
MCP_ENABLED=true
MCP_ALLOWED_HOSTS=["localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*", "192.168.1.50:10006"]
```

Restart the backend, allow the intended clients through the host/network firewall, and use `http://192.168.1.50:10006/api/v1/mcp/`. `0.0.0.0` is a listen address, not a client URL. These LAN settings are examples; the current local configuration continues to listen on `localhost`.

For clients in containers, use a host address reachable from the container (for example `host.docker.internal` where supported), expose the listening interface, and add the exact incoming host/port to `MCP_ALLOWED_HOSTS`. For a hosted project, provide a network route to the service or deploy it behind an HTTPS domain; a local loopback URL alone is insufficient.

For an HTTPS deployment, use `https://cnc.example.com/api/v1/mcp/`, enable MCP in the production environment, and configure the public Host in both `MCP_ALLOWED_HOSTS` and the application's `ALLOWED_HOSTS`. The existing Nginx deployment forwards `/api/v1` paths. Preserve Authorization and MCP protocol headers in any additional proxy.

If requests include an `Origin` header, add the calling web application's exact origin to `MCP_ALLOWED_ORIGINS`; this is the caller's origin, which may differ from the MCP server domain. Browser cross-origin calls must also pass the host application's CORS policy (`PROD_CORS_ORIGINS` in production). Backend-to-backend MCP clients normally omit Origin and do not require browser CORS configuration.

Tokens retain the normal application lifetime and revocation rules, including the configured sliding-session policy. When authentication expires or the session is revoked, obtain a current access token, update the consuming client's secret/header, and reconnect. If an integration refreshes its tokens through the existing authentication flow, update its stored access and refresh tokens from that response. The connection template cannot create a permanent machine token.

## Enable the endpoint

Install the updated backend dependencies using the existing database extra. For example, from `backend/` for PostgreSQL:

```powershell
uv sync --extra postgres
```

Add these values to the environment used to start the backend, or to `backend/env/.env.dev` for the development command below:

```dotenv
MCP_ENABLED=true
```

Start or restart the backend using its normal command:

```powershell
uv run --extra postgres main.py run --env=dev
```

Use the appropriate `mysql` or `sqlite` extra for those deployments. Production uses the existing `env/.env.prod` and `--env=prod` configuration.

| Setting | Default | Meaning |
| --- | --- | --- |
| `MCP_ENABLED` | `false` | Register the MCP endpoint and run its transport lifecycle. |
| `MCP_ALLOWED_HOSTS` | Loopback hostnames and optional ports | Host allowlist for the MCP transport. |
| `MCP_ALLOWED_ORIGINS` | HTTP loopback origins and optional ports | Allowed browser Origins for the MCP transport. Requests without an Origin still require authentication. |

For a deployed domain, explicitly configure the lists as JSON arrays:

```dotenv
MCP_ALLOWED_HOSTS=["cnc.example.com"]
MCP_ALLOWED_ORIGINS=["https://cnc.example.com"]
```

These values must agree with the host application's existing production trusted-host and CORS configuration. Add the exact host/port of a separate development proxy if it is used. Avoid a wildcard origin. Changes take effect after restarting the backend.

## URL and authentication

| Access path | Example URL |
| --- | --- |
| Direct backend | `http://127.0.0.1:8001/mcp/` |
| Existing API prefix, including Nginx/Vite proxy | `http://127.0.0.1:8001/api/v1/mcp/` |
| Deployed website | `https://cnc.example.com/api/v1/mcp/` |

The actual port and API prefix follow `SERVER_PORT` and `ROOT_PATH`. Keep the trailing slash in client configuration. The existing Nginx/Vite `/api/v1` proxy rule covers this endpoint. Custom proxies must preserve the path, Authorization header, and MCP protocol headers. Configure the MCP host allowlist for the public Host the backend receives.

Send the **application user's access token**, obtained through the normal system login:

```http
Authorization: Bearer <access_token>
```

Every request validates the existing Redis-backed session and current user. Refresh tokens, missing/invalid credentials, expired sessions, and revoked sessions cannot authorize MCP calls. Logout/session expiry affects MCP as it affects the existing APIs. Tokens in query parameters are not supported. This integration does not issue separate machine API keys or implement OAuth discovery/authorization.

Example configuration for clients that accept `mcpServers` with a remote URL and headers:

```json
{
  "mcpServers": {
    "cnc-management": {
      "url": "http://127.0.0.1:8001/api/v1/mcp/",
      "headers": {
        "Authorization": "Bearer <access_token>"
      }
    }
  }
}
```

The token belongs to the caller, whose normal permissions and data scope apply. A successful MCP connection does not grant all CNC tools.

## Tools and permissions

Exactly these six tools exist. `tools/list` returns the subset allowed by the caller's permissions. The same checks run on `tools/call`, so a client cannot execute an excluded tool by naming it directly.

| Tool | Required permission | Arguments |
| --- | --- | --- |
| `cnc_account_list` | `module_cnc:cnc_account:query` | `page_no`, `page_size`, `order_by`, `search` |
| `cnc_account_detail` | `module_cnc:cnc_account:detail` | `id` |
| `cnc_account_login` | `module_cnc:cnc_account:update` | `id`, `action` (default `start`), `session_id` for session actions |
| `cnc_account_decrypt_password` | `module_cnc:cnc_account:update` | `username` (exact account match) |
| `cnc_part_list` | `module_cnc:cnc_part:query` | `page_no`, `page_size`, `order_by`, `search` |
| `cnc_part_detail` | `module_cnc:cnc_part:detail` | `id` |

Generic record creation, editing, deletion, enable/disable changes, and drawing-authorization changes remain unavailable, including to superusers. Controlled login can update encrypted browser state and account leases through the existing login manager. There is no write-enable configuration. The earlier `MCP_ALLOW_WRITES` option has been removed.

Detail IDs must be positive integers. Pagination defaults to page 1, size 10, with a maximum page size of 100. Unknown argument fields are rejected. The schemas returned by `tools/list` describe the complete supported input.

Account search accepts the existing filters, including `platform_id`, `alias`, `username`, `login_method`, `session_status`, and `enabled`. Drawing search includes `file_name`, `extension`, `declared_unit`, `validation_status`, and `upload_authorized`. Both retain their audit/date filters and the existing role data scope. Ordinary users' account results additionally remain creator-scoped.

Drawing queries can return or filter the existing `upload_authorized` flag. The MCP Server cannot change that flag.

## Argument examples

Read the caller's available account records:

```json
{
  "page_no": 1,
  "page_size": 20,
  "search": {"enabled": true}
}
```

Find drawings by file name:

```json
{
  "page_no": 1,
  "page_size": 10,
  "order_by": [{"id": "desc"}],
  "search": {"file_name": "bracket"}
}
```

Read one permitted account with `cnc_account_detail`:

```json
{"id": 31}
```

Read one permitted drawing with `cnc_part_detail`:

```json
{"id": 42}
```

Drawing queries return management metadata. They do not transfer file bytes, inspect arbitrary paths, validate geometry, or submit files to vendors. `HEADER_VALID` retains its existing limited meaning of a basic STEP header check; it is not a manufacturability guarantee.

## Results, errors, and privacy

Successful tools return MCP text content and structured data. Account queries (`cnc_account_list` items and `cnc_account_detail`) return `id`, `username`, encrypted `password`, `platform_name`, `login_url`, and `quote_url`. Use `id` for login and `username` for password decryption. Drawing list items (`cnc_part_list`) return only `file_name` and `file_path`. Lists contain the normal page fields and `items`. These are native MCP responses, not the REST `code/msg/data` envelope.

The query `password` is an opaque Fernet-encrypted credential envelope (version, username, password), using the application's existing encryption key ring. It is not a plaintext password or a display mask and must not be submitted to a login form. Existing encrypted credentials are returned without decryption; legacy plaintext credentials are encrypted in memory without changing the query's database row. Only the independent decryption tool intentionally returns plaintext. Browser sessions, encryption keys and lease secrets are never returned. Rejected inputs and unexpected exceptions return fixed safe errors without reflecting request values or storage errors.

### 登录与独立密码解密调用说明

1. 用 `cnc_account_list` 查找账号，取得 `id`。列表和详情中的 `password` 始终为密文。
2. 自动登录调用 `cnc_account_login`，参数为 `{"id":31}` 或 `{"id":31,"action":"start"}`。后端从数据库加载账号并自动解密密码，无需调用方传递密码。
3. 登录返回 `session_id`、`account_id`、脱敏用户名、`status`、`reason`、`reused`、`viewport`、`expires_at`。使用 `{"id":31,"action":"status","session_id":"<start 返回的 session_id>"}` 查询进度。只有 `READY` 表示已核实平台账号身份；`STARTING`、`AUTHENTICATING` 表示处理中。
4. `WAITING_HUMAN` 表示需要用户在现有账号管理页面的登录窗口完成验证码等操作。MCP 不提供点击、键盘或验证码绕过工具。随后可用同一参数将 `action` 改为 `verify` 验证身份，或改为 `close` 关闭会话。
5. 如果调用方要自行在登录表单中填入密码，可独立调用 `cnc_account_decrypt_password`，参数 `{"username":"user@example.com"}`，传入登录账号（用户名/手机/邮箱），不传 `id`。返回 `{"id":31,"username":"user@example.com","password":"<明文密码>"}`，供登录使用，不应展示明文或写入调用方日志。此工具仅对当前用户可访问的账号做精确匹配；不存在、无权访问或存在多个同名账号时拒绝解密，不会选择第一条记录，也不接受任意密文。

登录与解密工具均要求 `module_cnc:cnc_account:update` 权限，并重新校验账号归属；解密复用账号服务的归属过滤和 CRUD 数据权限，排除软删除账号。普通用户不能解密或登录他人的账号。凭据解密复用 `read_credentials`，支持现有密钥轮换与历史凭据兼容。解密本身不启动浏览器或修改账号；自动登录无需先调用解密工具。

工具描述与 MCP annotations 已区分行为：查询和解密为只读、幂等；登录会访问外部平台、更新会话，标注为非只读、非幂等、开放世界操作。重启后端并刷新客户端工具列表后生效。登录需要已有 Playwright 浏览器运行环境；只通过协议测试不能证明真实平台已登录。

Troubleshooting:

- Missing endpoint: confirm `MCP_ENABLED=true` in the backend's actual environment and restart it.
- Authentication failure: use a current application access token and ensure its Redis session still exists.
- Empty or incomplete tool list: check query/detail permissions and account update permission for login/decryption.
- Host/Origin rejection: add the actual deployed host/origin to the MCP allowlists and align the normal production host/CORS settings.
- Storage or business error: inspect server-side safe metadata and existing CNC management behavior; a successful transport handshake does not prove a business operation succeeded.

Set `MCP_ENABLED=false` and restart to remove the endpoint. No MCP database migration or separate server process is required.

The application includes no external MCP-service connection manager, outbound OAuth client, MCP-client UI, or Agent MCP-client integration. Official SDK clients used by automated tests are protocol test harnesses only.
