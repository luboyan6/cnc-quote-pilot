import { request } from "@utils";

const API_PATH = "/cnc/cnc_quote_schedule";

export interface ScheduleTarget {
  config_id: number;
  account_id?: number | null;
  quantities: number[];
}

export interface ScheduleCreate {
  name: string;
  interval_minutes: number;
  timezone?: string;
  targets: ScheduleTarget[];
}

export interface ScheduleUpdate {
  name?: string;
  interval_minutes?: number;
  timezone?: string;
  targets?: ScheduleTarget[];
}

export interface ScheduleDetail {
  id: string;
  actor_id: number;
  name: string;
  interval_minutes: number;
  timezone: string;
  anchor_time?: string | null;
  next_run_at?: string | null;
  status: "ENABLED" | "PAUSED" | string;
  revision: number;
  last_round_at?: string | null;
  pause_reason?: string | null;
  target_snapshot?: {
    items?: Array<{
      config_id: number;
      account_id: number;
      file_name: string;
      requested: Record<string, unknown>;
    }>;
  } | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ScheduleRound {
  id: string;
  schedule_id: string;
  round_no: number;
  scheduled_for?: string | null;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "SKIPPED" | string;
  batch_id?: string | null;
  schedule_revision: number;
  skip_reason?: string | null;
  created_at?: string | null;
  finished_at?: string | null;
}

export interface ScheduleListResult {
  items: ScheduleDetail[];
  total: number;
}

const CncQuoteScheduleAPI = {
  create(data: ScheduleCreate, signal?: AbortSignal) {
    return request<ApiResponse<ScheduleDetail>>({
      url: `${API_PATH}/create`,
      method: "post",
      data,
      signal,
    });
  },

  update(id: string, data: ScheduleUpdate, signal?: AbortSignal) {
    return request<ApiResponse<ScheduleDetail>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data,
      signal,
    });
  },

  list(params?: { offset?: number; limit?: number }, signal?: AbortSignal) {
    return request<ApiResponse<ScheduleListResult>>({
      url: `${API_PATH}/list`,
      method: "get",
      params,
      signal,
    });
  },

  detail(id: string, signal?: AbortSignal) {
    return request<ApiResponse<ScheduleDetail>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
      signal,
    });
  },

  pause(id: string, signal?: AbortSignal) {
    return request<ApiResponse<ScheduleDetail>>({
      url: `${API_PATH}/${id}/pause`,
      method: "post",
      signal,
    });
  },

  resume(id: string, signal?: AbortSignal) {
    return request<ApiResponse<ScheduleDetail>>({
      url: `${API_PATH}/${id}/resume`,
      method: "post",
      signal,
    });
  },

  rounds(id: string, params?: { offset?: number; limit?: number }, signal?: AbortSignal) {
    return request<ApiResponse<ScheduleRound[]>>({
      url: `${API_PATH}/${id}/rounds`,
      method: "get",
      params,
      signal,
    });
  },
};

export default CncQuoteScheduleAPI;
