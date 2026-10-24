/** Read-only evidence capture for the two site-specific skills. No file selection. */
import { sendCommand } from 'file:///E:/DevelopmentKit/node_cache/_npx/15c61037b1978c83/node_modules/chrome-devtools-mcp/build/src/daemon/client.js';
import { appendFile } from 'node:fs/promises';

const mode = process.argv[2] || 'pages';
const pageId = Number(process.argv[3]);
const session = '1023c0de-0000-4000-8000-000000000001';
const evidence = new URL('./site-skill-browser-evidence.jsonl', import.meta.url);
const projection = `() => {
  if (location.hostname !== 'www.jlc-cnc.com') return { stopped: 'unexpected_host' };
  const visible = e => e.getBoundingClientRect().width > 0;
  return {
    host: location.hostname, path: location.pathname, hash: location.hash, title: document.title,
    uploads: [...document.querySelectorAll('input[type=file]')].map(e => ({id:e.id,accept:e.accept,multiple:e.multiple})),
    controls: [...document.querySelectorAll('button,[role=button],[role=combobox],select,#material-box .change-info')]
      .filter(visible).map(e => ({tag:e.tagName,id:e.id,role:e.getAttribute('role'),text:e.innerText.slice(0,180)})).slice(0,45),
    quantity: [...document.querySelectorAll('input[role=spinbutton]')].filter(visible).map(e=>({value:e.value,min:e.min,max:e.max})),
    text: document.body.innerText.slice(0,8500)
  };
}`;
let tool;
let args;
if (mode === 'pages') { tool = 'list_pages'; args = {}; }
else if (mode === 'open-jlc') {
  tool = 'new_page'; args = { url: 'https://www.jlc-cnc.com/cncOrder/#/placeOrder', background: true, timeout: 30000 };
}
else if (mode === 'inspect' && Number.isSafeInteger(pageId) && pageId > 2) {
  tool = 'evaluate_script'; args = { pageId, function: projection, waitForStableDom: false };
} else throw new Error('Use pages, open-jlc, or inspect with a newly created public page ID');
const response = await sendCommand({ method: 'invoke_tool', tool, args }, session, 45000);
const result = response.success ? JSON.parse(response.result) : { error: 'daemon_command_failed' };
const record = { time: new Date().toISOString(), tool, pageId, result };
await appendFile(evidence, JSON.stringify(record) + '\n', 'utf8');
console.log(JSON.stringify(record));
if (!response.success || result.isError) process.exitCode = 1;
