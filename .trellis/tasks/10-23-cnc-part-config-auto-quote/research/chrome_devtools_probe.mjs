/** Drive only this task's isolated official Chrome DevTools MCP daemon. */
import { readFile, appendFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

const daemonClient = process.env.CNC_DEVTOOLS_CLIENT ||
  'E:/DevelopmentKit/node_cache/_npx/15c61037b1978c83/node_modules/chrome-devtools-mcp/build/src/daemon/client.js';
const { sendCommand } = await import(pathToFileURL(daemonClient).href);
const session = '1023c0de-0000-4000-8000-000000000001';
const actionsPath = new URL('./chrome_devtools_actions.json', import.meta.url);
const evidencePath = new URL('./chrome-devtools-evidence-2026-10-23.jsonl', import.meta.url);
const allowed = new Set([
  'list_pages', 'new_page', 'navigate_page', 'resize_page', 'take_snapshot',
  'take_screenshot', 'evaluate_script', 'click', 'drag', 'fill', 'fill_form',
  'press_key', 'wait_for', 'list_network_requests', 'get_network_request',
  'list_console_messages', 'get_console_message', 'close_page',
]);

function redact(value) {
  if (Array.isArray(value)) return value.map(redact);
  if (value && typeof value === 'object') {
    if (value.type === 'image') return { type: 'image', omitted: true };
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [
      key, /^(authorization|cookie|set-cookie|access_token|refresh_token|password|secret)$/i.test(key)
        ? '[REDACTED]' : redact(item),
    ]));
  }
  if (typeof value !== 'string') return value;
  return value
    .replace(/(Bearer\s+)[A-Za-z0-9._~+\/-]+=*/gi, '$1[REDACTED]')
    .replace(/((?:authorization|cookie|set-cookie)\s*:\s*)[^\r\n]+/gi, '$1[REDACTED]')
    .replace(/("(?:access_token|refresh_token|password|secret)"\s*:\s*")[^"]*/gi, '$1[REDACTED]');
}

for (const action of JSON.parse(await readFile(actionsPath, 'utf8'))) {
  if (!allowed.has(action.tool)) throw new Error('Unsupported test tool');
  const response = await sendCommand({
    method: 'invoke_tool', tool: action.tool, args: action.args || {},
  }, session, 45000);
  const result = response.success ? JSON.parse(response.result) : { error: response.error };
  const resultView = result.content ? { content: result.content, ...(result.isError ? { isError: true } : {}) } : result;
  const record = redact({
    time: new Date().toISOString(), label: action.label, tool: action.tool, result: resultView,
  });
  await appendFile(evidencePath, JSON.stringify(record) + '\n', 'utf8');
  console.log(JSON.stringify(record));
  if (!response.success || result.isError) process.exitCode = 1;
}
