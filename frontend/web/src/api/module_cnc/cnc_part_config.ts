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
  confirmQuoteDeclaration(id: number, runId: string, data: CncQuoteDeclarationDecision) {
    return request<ApiResponse<CncQuoteRun>>({
      url: `${API_PATH}/${id}/quote/runs/${encodeURIComponent(runId)}/declaration`,
      method: "post",
      data: { declaration_id: data.declaration_id, choice: data.choice },
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

  getParamsCatalog(siteType?: number) {
    return request<ApiResponse<CncParamsCatalog>>({
      url: `${API_PATH}/params-catalog`,
      method: "get",
      params: siteType ? { site_type: siteType } : undefined,
    });
  },
};

export default CncPartConfigAPI;

// ------------------------------
// TS 类型声明
// ------------------------------

export interface CncParamItem {
  code: string;
  name: string;
  category?: string;
  is_default?: boolean;
  requires_2d_drawing?: boolean;
  options_schema?: Record<string, unknown>;
  properties?: Record<string, unknown>;
  description?: string;
  supported_finishes?: string[];
  supported_tolerances?: string[];
  supported_roughnesses?: string[];
}

export interface CncParamsCatalog {
  platform_code?: string;
  material_categories?: string[];
  materials?: CncParamItem[];
  surface_finishes?: CncParamItem[];
  tolerances?: CncParamItem[];
  roughnesses?: CncParamItem[];
  subprocesses?: CncParamItem[];
  inspections?: CncParamItem[];
  certifications?: CncParamItem[];
  markings?: CncParamItem[];
  delivery_tiers?: CncParamItem[];
}

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
  tolerance?: string;
  requires_2d_drawing?: boolean;
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
  material_category?: string;
  material_code?: string;
  subprocess_code?: string;
  surface_finish_code?: string;
  surface_finish_options_json?: Record<string, unknown>;
  tolerance?: string;
  roughness?: string;
  has_threads?: boolean;
  thread_count?: number;
  has_inserts?: boolean;
  insert_count?: number;
  inspection_code?: string;
  certification_code?: string;
  marking_code?: string;
  marking_text?: string;
  delivery_code?: string;
  requires_2d_drawing?: boolean;
  drawing_2d_file_id?: number;
  technical_notes?: string;
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
  material_category?: string;
  material_code?: string;
  subprocess_code?: string;
  surface_finish_code?: string;
  surface_finish_options_json?: Record<string, unknown>;
  tolerance?: string;
  roughness?: string;
  has_threads?: boolean;
  thread_count?: number;
  has_inserts?: boolean;
  insert_count?: number;
  inspection_code?: string;
  certification_code?: string;
  marking_code?: string;
  marking_text?: string;
  delivery_code?: string;
  requires_2d_drawing?: boolean;
  drawing_2d_file_id?: number;
  technical_notes?: string;
}

export interface CncQuoteAccount {
  id: number;
  alias: string;
  masked_username: string;
}

export type CncQuoteDeclarationChoice = "not_controlled" | "controlled";

export interface CncQuoteExportDeclaration {
  declaration_id: string;
  statement: string;
  options: { value: CncQuoteDeclarationChoice; label: string }[];
}

export interface CncQuoteDeclarationDecision {
  declaration_id: string;
  choice: CncQuoteDeclarationChoice;
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

export interface CncLeadTimeTier {
  tier: string;
  days: string;
  part_amount?: string;
  tax_amount?: string;
  total_amount?: string;
  discount_amount?: string;
  estimated_ship_date?: string;
}

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
  tax_amount?: string | null;
  total_amount?: string | null;
  discount_amount?: string | null;
  lead_time_tiers?: CncLeadTimeTier[] | null;
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
  export_declaration?: CncQuoteExportDeclaration | null;
}
