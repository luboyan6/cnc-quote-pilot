import { request } from "@utils";

// API 前缀来自分系统包 module_xxx → /xxx
// 对齐 module_example/demo：业务接口固定为 /{prefix}/{module_name}
const API_PATH = "/cnc/cnc_platform";

const CncPlatformAPI = {
  listCncPlatform(query: CncPlatformPageQuery) {
    return request<ApiResponse<PageResult<CncPlatformTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailCncPlatform(query: number) {
    return request<ApiResponse<CncPlatformTable>>({
      url: `${API_PATH}/detail/${query}`,
      method: "get",
    });
  },

  createCncPlatform(body: CncPlatformForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  updateCncPlatform(id: number, body: CncPlatformForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  deleteCncPlatform(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },

  batchCncPlatform(body: BatchType) {
    return request<ApiResponse>({
      url: `${API_PATH}/status/batch`,
      method: "patch",
      data: body,
    });
  },

  exportCncPlatform(body: CncPlatformPageQuery) {
    return request<Blob>({
      url: `${API_PATH}/export`,
      method: "post",
      data: body,
      responseType: "blob",
    });
  },

  downloadTemplateCncPlatform() {
    return request<Blob>({
      url: `${API_PATH}/download/template`,
      method: "post",
      responseType: "blob",
    });
  },

  importCncPlatform(body: FormData) {
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

export default CncPlatformAPI;

// ------------------------------
// TS 类型声明
// ------------------------------

/** 列表查询参数 */
export interface CncPlatformPageQuery extends PageQuery, UserByQueryParams {
  name?: string;
  login_url?: string;
  quote_entry_url?: string;
}

/** 列表展示项 */
export interface CncPlatformTable extends BaseType {
  name?: string;
  login_url?: string;
  quote_entry_url?: string;
}

/** 新增/修改表单参数 */
export interface CncPlatformForm extends BaseFormType {
  name?: string;
  login_url?: string;
  quote_entry_url?: string;
}
