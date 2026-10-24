<script setup lang="ts">
import { ref } from 'vue';
import AutoQuoteDialog from '@quote-ui/AutoQuoteDialog.vue';
const scenario = new URLSearchParams(location.search).get('scenario') || 'quote';
const selected = ref<number>();
const requested = { material: 'Aluminum 6061-T6', quantity: '3', surface_finish: 'Bead Blast', tolerance: 'ISO 2768-m' };
const run = scenario === 'picker' ? undefined : {
  run_id: 'synthetic-run', config_id: 42, account_id: 7,
  platform_name: '本地合成平台', masked_username: 'u***@example.com',
  file_name: 'bracket-with-very-long-local-filename-for-layout-inspection.step',
  status: scenario === 'human' ? 'WAITING_HUMAN' : scenario === 'estimate' ? 'REFERENCE_ESTIMATE' : 'QUOTED',
  stage: scenario === 'human' ? 'login' : 'complete',
  reason: scenario === 'human' ? 'CHALLENGE_REQUIRED' : scenario === 'estimate' ? 'PROVIDER_REFERENCE_ESTIMATE' : 'QUOTE_VERIFIED',
  can_input: scenario === 'human', requested, viewport: { width: 1280, height: 720 },
  expires_at: '2026-10-23T12:00:00Z',
  result: scenario === 'human' ? null : {
    status: scenario === 'estimate' ? 'REFERENCE_ESTIMATE' : 'QUOTED',
    amount: '123456.78901234', currency: 'USD', price_scope: 'unit',
    lead_time: { text: 'Ships in 5 business days' }, effective: requested,
    priced_at: '2026-10-23T10:00:00Z', observed_at: '2026-10-23T10:00:01Z',
    tax_included: null, shipping_included: null,
  },
};
const frame = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720"><rect width="1280" height="720" fill="#eef2f6"/><rect x="400" y="170" width="480" height="330" fill="white" stroke="#c3cad3"/><text x="450" y="230" font-size="26" fill="#283445">Local synthetic login</text><rect x="450" y="275" width="380" height="50" fill="#f4f6f8"/><text x="465" y="307" font-size="20">Verification code</text><rect x="450" y="360" width="180" height="50" fill="#409eff"/><text x="485" y="393" font-size="20" fill="white">Continue</text></svg>');
</script>
<template>
  <p style="padding:20px">本地合成 UI 验证 · 不连接业务或平台 API</p>
  <AutoQuoteDialog :visible="true" config-name="加工配置" :run="run" :accounts="[{ id: 7, alias: '生产账号', masked_username: 'u***@example.com' }, { id: 9, alias: '备用账号', masked_username: 'b***@example.com' }]" :selected-account="selected" :choosing-account="scenario === 'picker'" :frame-url="scenario === 'human' ? frame : ''" error="" :busy="false" :interactive="scenario === 'human'" @select-account="selected = $event" />
</template>
