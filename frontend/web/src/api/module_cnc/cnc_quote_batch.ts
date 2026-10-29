import { request } from "@utils";

const API_PATH = "/cnc/cnc_quote_batch";

export interface BatchTarget {
  config_id: number;
  account_id?: number | null;
  quantities: number[];
}

export interface BatchRequest {
  request_id: string;
  targets: BatchTarget[];
}

export interface BatchItem {
  id: string;
  batch_id: string;
  config_id: number;
  account_id: number;
  exec_status: string;
  quote_kind?: string | null;
  run_id?: string | null;
  attempt_count: number;
  max_attempts: number;
  error_code?: string | null;
  next_attempt_at?: string | null;
  cancel_requested_at?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  row_version: number;
  requested: {
    quantity?: string;
    material?: string;
    surface_finish?: string;
    tolerance?: string;
    roughness?: string;
    [key: string]: unknown;
  };
  file_name: string;
}

export interface BatchDetail {
  id: string;
  request_id: string;
  source: string;
  status: string;
  counts: Record<string, number>;
  item_count: number;
  cancel_requested_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BatchListResult {
  items: BatchDetail[];
  total: number;
}

export interface BatchPreviewItem {
  config_id: number;
  account_id: number;
  file_name: string;
  requested: Record<string, unknown>;
}

export interface BatchPreviewResult {
  item_count: number;
  items: BatchPreviewItem[];
}

export interface BatchAttempt {
  attempt_no: number;
  run: Record<string, any>;
}

const CncQuoteBatchAPI = {
  preview(data: BatchRequest, signal?: AbortSignal) {
    return request<ApiResponse<BatchPreviewResult>>({
      url: `${API_PATH}/preview`,
      method: "post",
      data,
      signal,
    });
  },

  create(data: BatchRequest, signal?: AbortSignal) {
    return request<ApiResponse<BatchDetail>>({
      url: `${API_PATH}/create`,
      method: "post",
      data,
      signal,
    });
  },

  list(params?: { offset?: number; limit?: number }, signal?: AbortSignal) {
    return request<ApiResponse<BatchListResult>>({
      url: `${API_PATH}/list`,
      method: "get",
      params,
      signal,
    });
  },

  detail(id: string, signal?: AbortSignal) {
    return request<ApiResponse<BatchDetail>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
      signal,
    });
  },

  items(id: string, params?: { offset?: number; limit?: number }, signal?: AbortSignal) {
    return request<ApiResponse<BatchItem[]>>({
      url: `${API_PATH}/${id}/items`,
      method: "get",
      params,
      signal,
    });
  },

  cancel(id: string, signal?: AbortSignal) {
    return request<ApiResponse<void>>({
      url: `${API_PATH}/${id}/cancel`,
      method: "post",
      signal,
    });
  },

  attempts(itemId: string, signal?: AbortSignal) {
    return request<ApiResponse<BatchAttempt[]>>({
      url: `${API_PATH}/items/${itemId}/attempts`,
      method: "get",
      signal,
    });
  },

  retryItem(itemId: string, signal?: AbortSignal) {
    return request<ApiResponse<void>>({
      url: `${API_PATH}/items/${itemId}/retry`,
      method: "post",
      signal,
    });
  },
};

export default CncQuoteBatchAPI;
