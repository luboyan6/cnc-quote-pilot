import { request } from "@utils";

// API 前缀来自分系统包 module_xxx → /xxx
// 对齐 module_example/demo：业务接口固定为 /{prefix}/{module_name}
const API_PATH = "/cnc/cnc_part";

const CncPartAPI = {
  listCncPart(query: CncPartPageQuery) {
    return request<ApiResponse<PageResult<CncPartTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailCncPart(query: number) {
    return request<ApiResponse<CncPartTable>>({
      url: `${API_PATH}/detail/${query}`,
      method: "get",
    });
  },

  createCncPart(body: CncPartForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  updateCncPart(id: number, body: CncPartForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  deleteCncPart(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },

  batchCncPart(body: BatchType) {
    return request<ApiResponse>({
      url: `${API_PATH}/status/batch`,
      method: "patch",
      data: body,
    });
  },

  exportCncPart(body: CncPartPageQuery) {
    return request<Blob>({
      url: `${API_PATH}/export`,
      method: "post",
      data: body,
      responseType: "blob",
    });
  },

  downloadTemplateCncPart() {
    return request<Blob>({
      url: `${API_PATH}/download/template`,
      method: "post",
      responseType: "blob",
    });
  },

  importCncPart(body: FormData) {
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

export default CncPartAPI;

// ------------------------------
// TS 类型声明
// ------------------------------

/** 列表查询参数 */
export interface CncPartPageQuery extends PageQuery, UserByQueryParams {
  extension?: string;
  size_bytes?: number;
  declared_unit?: string;
  validation_status?: string;
  upload_authorized?: boolean;
  file_path?: string;
  file_name?: string;
  file_type?: number;
}

/** 列表展示项 */
export interface CncPartTable extends BaseType {
  extension?: string;
  size_bytes?: number;
  declared_unit?: string;
  validation_status?: string;
  upload_authorized?: boolean;
  file_path?: string;
  file_name?: string;
  file_type?: number;
}

/** 新增/修改表单参数 */
export interface CncPartForm extends BaseFormType {
  extension?: string;
  size_bytes?: number;
  declared_unit?: string;
  validation_status?: string;
  upload_authorized?: boolean;
  file_path?: string;
  file_name?: string;
  file_type?: number;
}
