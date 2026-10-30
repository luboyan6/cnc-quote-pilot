import { request } from "@utils";

const API_PATH = "/cnc/cnc_quote_result";

const CncQuoteResultAPI = {
  listCncQuoteResult(query: CncQuoteResultPageQuery, signal?: AbortSignal) {
    return request<ApiResponse<PageResult<CncQuoteResultTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
      signal,
    });
  },

  detailCncQuoteResult(id: number, signal?: AbortSignal) {
    return request<ApiResponse<CncQuoteResultTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
      signal,
    });
  },

  getQuoteStats(params?: CncQuoteResultPageQuery, signal?: AbortSignal) {
    return request<ApiResponse<CncQuoteStats>>({
      url: `${API_PATH}/stats`,
      method: "get",
      params,
      signal,
    });
  },

  getHistoryPrices(
    params?: {
      part_id?: number;
      config_id?: number;
      platform_id?: number;
      batch_id?: string;
      round_id?: string;
      quote_kind?: string;
      currency?: string;
      comparison_key?: string;
      limit?: number;
    },
    signal?: AbortSignal
  ) {
    return request<ApiResponse<CncHistoryPricePoint[]>>({
      url: `${API_PATH}/history-prices`,
      method: "get",
      params,
      signal,
    });
  },

  deleteCncQuoteResult(ids: number[], signal?: AbortSignal) {
    return request<ApiResponse<void>>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: ids,
      signal,
    });
  },

  getScreenshotUrl(id: number) {
    const baseApi = import.meta.env.VITE_APP_BASE_API || "/api/v1";
    return `${baseApi}${API_PATH}/screenshot/${id}`;
  },

  getScreenshotBlob(id: number, signal?: AbortSignal) {
    return request<Blob>({
      url: `${API_PATH}/screenshot/${id}`,
      method: "get",
      responseType: "blob",
      signal,
    });
  },

  getPrivateScreenshotBlob(id: number, signal?: AbortSignal) {
    return request<Blob>({
      url: `${API_PATH}/screenshot/${id}`,
      method: "get",
      params: { private_only: true },
      responseType: "blob",
      signal,
    });
  },
};

export default CncQuoteResultAPI;

// ------------------------------
// TS 类型声明
// ------------------------------

export interface CncQuoteResultPageQuery extends PageQuery, UserByQueryParams {
  order_by?: string;
  config_id?: number;
  part_id?: number;
  platform_id?: number;
  batch_id?: string;
  round_id?: string;
  quote_status?: string;
  quote_kind?: string;
  success?: boolean;
  part_name?: string;
  config_name?: string;
  currency?: string;
  comparison_key?: string;
  created_time_start?: string;
  created_time_end?: string;
}

export interface CncQuoteResultTable extends BaseType {
  run_id?: string;
  batch_id?: string | null;
  item_id?: string | null;
  round_id?: string | null;
  config_id?: number;
  config_name?: string;
  part_id?: number;
  part_name?: string;
  platform_id?: number;
  platform_code?: string;
  platform_name?: string;
  account_id?: number;
  account_alias?: string;

  quote_status?: string;
  success?: boolean;

  unit_price?: number | string | null;
  total_amount?: number | string | null;
  tax_amount?: number | string | null;
  discount_amount?: number | string | null;
  shipping_amount?: number | string | null;
  tax_included?: boolean | null;
  currency?: string | null;
  price_scope?: string | null;

  lead_time_raw?: string | null;
  lead_time_json?: Record<string, unknown> | null;
  platform_quote_id?: string | null;

  material?: string | null;
  surface_finish?: string | null;
  quantity?: number;
  tolerance?: string | null;
  roughness?: string | null;
  extra_params?: Record<string, unknown> | null;
  file_sha256?: string | null;
  comparison_key?: string | null;
  comparison_version?: number | null;
  effective_snapshot?: Record<string, unknown> | null;

  elapsed_ms?: number;
  duration_seconds?: number | string | null;
  queue_ms?: number;
  active_execution_ms?: number;
  human_wait_ms?: number;
  reconcile_ms?: number;
  total_wall_ms?: number;

  evidence_id?: string | null;
  evidence_state?: string | null;
  evidence_screenshot?: string | null;
  quoted_at?: string | null;
  observed_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
}

export interface CncPlatformStat {
  platform_id: number | null;
  platform_name: string | null;
  platform_code: string | null;
  total_quotes: number;
  formal_quotes: number;
  reference_estimates: number;
  pending_reviews: number;
  success_quotes: number;
  failed_quotes: number;
  success_rate: number;
  formal_quote_rate?: string | null;
  avg_duration_seconds: number;
  min_unit_price: string | number | null;
  max_unit_price: string | number | null;
  currency: string | null;
  latest_quote_time: string | null;
}

export interface CncQuoteStats {
  total_quotes: number;
  total_items: number;
  completed_quotes: number;
  quoted_quotes: number;
  reference_estimate_quotes: number;
  pending_review_quotes: number;
  success_quotes: number;
  failed_quotes: number;
  cancelled_quotes: number;
  waiting_human_quotes: number;
  reconciling_quotes: number;
  overall_success_rate: number;
  completion_rate?: string | null;
  formal_quote_rate?: string | null;
  avg_duration_seconds: number;
  avg_queue_seconds: number;
  avg_exec_seconds: number;
  fastest_seconds: number;
  longest_seconds: number;
  platform_stats: CncPlatformStat[];
}

export interface CncHistoryPricePoint {
  id: number;
  config_id?: number | null;
  config_name?: string | null;
  part_id?: number | null;
  part_name?: string | null;
  platform_id: number | null;
  platform_name: string | null;
  platform_code?: string | null;
  unit_price: string | number;
  total_amount?: string | number | null;
  price_diff?: string | null;
  change_rate?: string | null;
  currency: string | null;
  quantity: number | null;
  quote_kind: string;
  comparison_key?: string | null;
  material?: string | null;
  surface_finish?: string | null;
  duration_seconds: number | null;
  evidence_id?: string | null;
  evidence_screenshot?: string | null;
  quoted_time?: string | null;
  observed_at?: string | null;
}
