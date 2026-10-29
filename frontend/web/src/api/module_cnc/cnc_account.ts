import { request } from "@utils";

// API 前缀来自分系统包 module_xxx → /xxx
// 对齐 module_example/demo：业务接口固定为 /{prefix}/{module_name}
const API_PATH = "/cnc/cnc_account";

/** Detail metadata is merged into CRUD form state; only send writable fields. */
function accountWriteBody(body: CncAccountForm) {
  return {
    platform_id: body.platform_id,
    alias: body.alias,
    username: body.username,
    password: body.password === "" ? undefined : body.password,
    login_url: body.login_url,
    login_method: body.login_method,
    enabled: body.enabled,
    authorization_note: body.authorization_note,
  };
}

const CncAccountAPI = {
  login(id: number) {
    return request<ApiResponse<CncLoginSession>>({
      url: `${API_PATH}/login/${id}`,
      method: "post",
    });
  },

  loginStatus(id: number, sessionId: string, signal?: AbortSignal) {
    return request<ApiResponse<CncLoginSession>>({
      url: `${API_PATH}/login/${id}/sessions/${encodeURIComponent(sessionId)}`,
      method: "get",
      signal,
    });
  },

  loginFrame(id: number, sessionId: string, signal?: AbortSignal) {
    return request<Blob>({
      url: `${API_PATH}/login/${id}/sessions/${encodeURIComponent(sessionId)}/frame`,
      method: "get",
      responseType: "blob",
      signal,
    });
  },

  loginInput(id: number, sessionId: string, data: CncLoginInput) {
    return request<ApiResponse<CncLoginSession>>({
      url: `${API_PATH}/login/${id}/sessions/${encodeURIComponent(sessionId)}/input`,
      method: "post",
      data,
    });
  },

  verifyLogin(id: number, sessionId: string) {
    return request<ApiResponse<CncLoginSession>>({
      url: `${API_PATH}/login/${id}/sessions/${encodeURIComponent(sessionId)}/verify`,
      method: "post",
    });
  },

  closeLogin(id: number, sessionId: string) {
    return request<ApiResponse>({
      url: `${API_PATH}/login/${id}/sessions/${encodeURIComponent(sessionId)}`,
      method: "delete",
    });
  },

  listCncAccount(query: CncAccountPageQuery) {
    return request<ApiResponse<PageResult<CncAccountTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailCncAccount(query: number) {
    return request<ApiResponse<CncAccountTable>>({
      url: `${API_PATH}/detail/${query}`,
      method: "get",
    });
  },

  createCncAccount(body: CncAccountForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/create`,
      method: "post",
      data: accountWriteBody(body),
    });
  },

  updateCncAccount(id: number, body: CncAccountForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: accountWriteBody(body),
    });
  },

  deleteCncAccount(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },

  batchCncAccount(body: BatchType) {
    return request<ApiResponse>({
      url: `${API_PATH}/status/batch`,
      method: "patch",
      data: body,
    });
  },

  exportCncAccount(body: CncAccountPageQuery) {
    return request<Blob>({
      url: `${API_PATH}/export`,
      method: "post",
      data: body,
      responseType: "blob",
    });
  },

  downloadTemplateCncAccount() {
    return request<Blob>({
      url: `${API_PATH}/download/template`,
      method: "post",
      responseType: "blob",
    });
  },

  importCncAccount(body: FormData) {
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

export default CncAccountAPI;

// ------------------------------
// TS 类型声明
// ------------------------------

/** 列表查询参数 */
export interface CncAccountPageQuery extends PageQuery, UserByQueryParams {
  platform_id?: number | string;
  alias?: string;
  username?: string;
  login_url?: string;
  login_method?: string;
  session_status?: string;
  last_verified_at_start?: string;
  last_verified_at_end?: string;
  auth_expires_at_start?: string;
  auth_expires_at_end?: string;
  enabled?: boolean;
  authorization_note?: string;
}

/** 列表展示项 */
export interface CncAccountTable extends BaseType {
  platform_id?: number | string;
  platform_name?: string;
  platform_login_url?: string;
  platform_quote_entry_url?: string;
  alias?: string;
  username?: string;
  login_url?: string;
  login_method?: string;
  has_credentials?: boolean;
  session_status?: string;
  last_verified_at?: string;
  auth_expires_at?: string;
  enabled?: boolean;
  authorization_note?: string;
}

/** 新增/修改表单参数 */
export interface CncAccountForm extends BaseFormType {
  platform_id?: number | string;
  alias?: string;
  username?: string;
  password?: string;
  login_url?: string;
  login_method?: string;
  enabled?: boolean;
  authorization_note?: string;
}

export type CncLoginStatus =
  | "STARTING"
  | "AUTHENTICATING"
  | "READY"
  | "WAITING_HUMAN"
  | "FAILED"
  | "CLOSED";

/** Private browser reference; no provider credentials or authenticated URLs. */
export interface CncLoginSession {
  session_id: string;
  account_id: number;
  platform_name: string;
  username: string;
  status: CncLoginStatus;
  reason: string | null;
  reused: boolean;
  viewport: { width: number; height: number };
  expires_at: string;
}

export type CncLoginInput =
  | { kind: "click"; x: number; y: number }
  | { kind: "drag"; x: number; y: number; x2: number; y2: number }
  | { kind: "scroll"; delta_x: number; delta_y: number }
  | { kind: "key"; key: CncLoginKey }
  | { kind: "text"; text: string };

export type CncLoginKey =
  | "Enter"
  | "Tab"
  | "Shift+Tab"
  | "Backspace"
  | "Delete"
  | "Escape"
  | "ArrowUp"
  | "ArrowDown"
  | "ArrowLeft"
  | "ArrowRight"
  | "Space";
