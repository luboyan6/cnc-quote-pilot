import type { CncPlatformStat } from "@/api/module_cnc/cnc_quote_result";

export function formatAmount(
  amount: string | number | null | undefined,
  currency: string | null | undefined
): string {
  if (amount == null || String(amount).trim() === "") return "未知";
  const code = currency?.trim().toUpperCase();
  if (code === "USD") return `$${amount}`;
  if (code === "CNY") return `¥${amount}`;
  return code ? `${code} ${amount}` : `${amount}（币种未知）`;
}

/** A platform may have separate rows per currency or platform name. */
export function summarizePlatformStats(rows: CncPlatformStat[], code: string) {
  const matches = rows.filter((row) => row.platform_code === code);
  if (!matches.length) return null;
  const totals = matches.reduce(
    (sum, row) => ({
      total: sum.total + row.total_quotes,
      quoted: sum.quoted + row.formal_quotes,
      reference: sum.reference + row.reference_estimates,
      review: sum.review + row.pending_reviews,
      failed: sum.failed + row.failed_quotes,
    }),
    { total: 0, quoted: 0, reference: 0, review: 0, failed: 0 }
  );
  const finished = totals.quoted + totals.reference + totals.review + totals.failed;
  return {
    total_quotes: totals.total,
    success_rate: finished ? ((totals.quoted + totals.reference) / finished) * 100 : null,
    formal_quote_rate: finished ? `${((totals.quoted / finished) * 100).toFixed(1)}%` : null,
  };
}
