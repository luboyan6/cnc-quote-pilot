import { request } from "@utils";

// API 前缀来自分系统包 module_xxx → /xxx
// 对齐 module_example/demo：业务接口固定为 /{prefix}/{module_name}
const API_PATH = "/cnc/cnc_part_config";

const CncPartConfigAPI = {
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
