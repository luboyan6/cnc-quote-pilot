import { request } from "@utils";
import type { CncLoginInput } from "./cnc_account";

// API 前缀来自分系统包 module_xxx → /xxx
// 对齐 module_example/demo：业务接口固定为 /{prefix}/{module_name}
const API_PATH = "/cnc/cnc_part_config";

const CncPartConfigAPI = {
  quoteAccounts(id: number, signal?: AbortSignal) {
    return request<ApiResponse<CncQuoteAccount[]>>({
      url: `${API_PATH}/${id}/quote/accounts`,
      method: "get",
      signal,
    });
  },
  startQuote(id: number, data: { request_id: string; account_id?: number }) {
    return request<ApiResponse<CncQuoteRun>>({
      url: `${API_PATH}/${id}/quote/runs`,
      method: "post",
      data: { request_id: data.request_id, account_id: data.account_id },
    });
  },
  quoteStatus(id: number, runId: string, signal?: AbortSignal) {
    return request<ApiResponse<CncQuoteRun>>({
      url: `${API_PATH}/${id}/quote/runs/${encodeURIComponent(runId)}`,
      method: "get",
      signal,
    });
  },
  quoteFrame(id: number, runId: string, signal?: AbortSignal) {
    return request<Blob>({
      url: `${API_PATH}/${id}/quote/runs/${encodeURIComponent(runId)}/frame`,
      method: "get",
      responseType: "blob",
      signal,
    });
  },
  quoteInput(id: number, runId: string, data: CncLoginInput) {
    return request<ApiResponse<CncQuoteRun>>({
      url: `${API_PATH}/${id}/quote/runs/${encodeURIComponent(runId)}/input`,
      method: "post",
      data,
    });
  },
  resumeQuote(id: number, runId: string) {
    return request<ApiResponse<CncQuoteRun>>({
      url: `${API_PATH}/${id}/quote/runs/${encodeURIComponent(runId)}/resume`,
      method: "post",
    });
  },
  cancelQuote(id: number, runId: string) {
    return request<ApiResponse<CncQuoteRun>>({
      url: `${API_PATH}/${id}/quote/runs/${encodeURIComponent(runId)}`,
      method: "delete",
    });
  },
  listCncPartConfig(query: CncPartConfigPageQuery) {
    return request<ApiResponse<PageResult<CncPartConfigTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailCncPartConfig(query: number) {
    return request<ApiResponse<CncPartConfigTable>>({
      url: `${API_PATH}/detail/${query}`,
      method: "get",
    });
  },

  createCncPartConfig(body: CncPartConfigForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  updateCncPartConfig(id: number, body: CncPartConfigForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  deleteCncPartConfig(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },

  batchCncPartConfig(body: BatchType) {
    return request<ApiResponse>({
      url: `${API_PATH}/status/batch`,
      method: "patch",
      data: body,
    });
  },

  exportCncPartConfig(body: CncPartConfigPageQuery) {
    return request<Blob>({
      url: `${API_PATH}/export`,
      method: "post",
      data: body,
      responseType: "blob",
    });
  },

  downloadTemplateCncPartConfig() {
    return request<Blob>({
      url: `${API_PATH}/download/template`,
      method: "post",
      responseType: "blob",
    });
  },

  importCncPartConfig(body: FormData) {
    return request<ApiResponse>({
      url: `${API_PATH}/import`,
      method: "post",
      data: body,
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
  },
};

export default CncPartConfigAPI;

// ------------------------------
// TS 类型声明
// ------------------------------

/** 列表查询参数 */
export interface CncPartConfigPageQuery extends PageQuery, UserByQueryParams {
  name?: string;
  site_type?: number;
  material?: string;
  quantity?: number;
  surface_finish?: string;
  extra_params?: Record<string, unknown>;
  enabled?: boolean;
  part_id?: number;
}

/** 列表展示项 */
export interface CncPartConfigTable extends BaseType {
  name?: string;
  site_type?: number;
  material?: string;
  quantity?: number;
  surface_finish?: string;
  extra_params?: Record<string, unknown>;
  enabled?: boolean;
  part_id?: number;
}

/** 新增/修改表单参数 */
export interface CncPartConfigForm extends BaseFormType {
  name?: string;
  site_type?: number;
  material?: string;
  quantity?: number;
  surface_finish?: string;
  extra_params?: Record<string, unknown>;
  enabled?: boolean;
  part_id?: number;
}

export interface CncQuoteAccount {
  id: number;
  alias: string;
  masked_username: string;
}

export type CncQuoteStatus =
  | "STARTING"
  | "AUTHENTICATING"
  | "RUNNING"
  | "WAITING_HUMAN"
  | "QUOTED"
  | "REFERENCE_ESTIMATE"
  | "PENDING_REVIEW"
  | "FAILED"
  | "CANCELLED";
export type CncQuoteStage =
  | "prepare"
  | "login"
  | "upload"
  | "parse"
  | "configure"
  | "quote"
  | "persist"
  | "complete";

export interface CncQuoteResult {
  status: "QUOTED" | "REFERENCE_ESTIMATE" | "PENDING_REVIEW";
  amount: string | null;
  currency: string | null;
  price_scope: "unit" | "line" | null;
  lead_time: Record<string, unknown> | null;
  effective: Record<string, string>;
  priced_at: string | null;
  observed_at: string;
  tax_included: boolean | null;
  shipping_included: boolean | null;
  freshness?: string | null;
}

/** Private run snapshot; credentials, remote URLs and server paths never enter this view. */
export interface CncQuoteRun {
  run_id: string;
  config_id: number;
  account_id: number;
  platform_name: string;
  masked_username: string;
  file_name: string;
  status: CncQuoteStatus;
  stage: CncQuoteStage;
  reason: string | null;
  viewport: { width: number; height: number };
  expires_at: string;
  can_input: boolean;
  requested: Record<string, string>;
  result: CncQuoteResult | null;
}
