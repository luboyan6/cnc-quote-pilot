/** Fixed provider/runtime reasons; unknown server content must stay out of UI text. */
const reasons: Record<string, string> = {
  QUOTE_PARAMETERS_INVALID: "加工参数格式无效，请检查材料、数量和差异化参数。",
  THIRD_PARTY_UPLOAD_NOT_AUTHORIZED: "此图纸尚未授权上传至第三方平台，请先修改图纸配置。",
  CONFIGURATION_UNAVAILABLE: "配置不存在或无权访问，请刷新列表。",
  CONFIGURATION_DISABLED: "此配置已停用，请启用后重试。",
  PART_UNAVAILABLE: "关联图纸不存在或不可用，请检查图纸配置。",
  PLATFORM_CONFIGURATION_INVALID: "平台地址或配置无效，请检查报价平台配置。",
  ACCOUNT_UNAVAILABLE: "所选账号不存在、已停用或无权使用，请检查账号配置。",
  ACCOUNT_PLATFORM_MISMATCH: "所选账号与配置平台不一致，请重新选择。",
  CONFIGURATION_BUSY: "此配置已有活动报价，请等待当前运行结束。",
  QUOTE_INPUT_CHANGED: "本次配置、图纸或账号已变更，报价已停止，请重新发起。",
  QUOTE_ACTOR_UNAVAILABLE: "后台用户已停用或删除，自动报价已停止。",
  QUOTE_PERMISSION_REVOKED: "自动报价权限已撤销，请重新登录或联系管理员。",
  FILE_INVALID: "图纸文件无法通过校验，请检查文件格式和内容。",
  PROVIDER_AUTOMATION_UNVERIFIED: "此平台的自动上传和报价尚未通过验证，无法继续自动操作。",
  FILE_EXCEEDS_PROVIDER_LIMIT: "图纸超过平台允许的文件大小，请更换文件。",
  QUOTE_WORKER_UNAVAILABLE_NO_RETRY: "本次报价执行服务已不可用，平台操作尚待核对，未重复发送。",
  QUOTE_WORKER_ACTIVE_CANNOT_CANCEL: "本次报价仍由其他执行服务占用，请等待服务释放后再核对状态。",
  QUOTE_MANUAL_INPUT_NOT_ALLOWED: "当前阶段不接受人工输入，请等待自动流程或检查运行状态。",
  QUOTE_RUN_CLOSED: "本次报价运行已关闭。",
  QUOTE_RUN_UNAVAILABLE: "本次报价运行不存在或无权访问。",
  QUOTE_STARTING: "正在准备本次图纸和加工参数。",
  UPLOADING_FILE: "正在上传本次关联图纸。",
  SETTING_PARAMETERS: "正在设置并核对加工参数。",
  FETCHING_QUOTE: "正在读取本次平台报价。",
  VALIDATING_QUOTE: "正在核验并保存平台报价。",
  QUOTE_VERIFIED: "已取得并保存本次平台报价。",
  QUOTE_CANCELLED: "本次运行已停止，已发送的操作记录仍保留。",
  QUOTE_CANCELLED_AFTER_LEASE_EXPIRY: "本次运行已在会话失效后停止，未确认的平台操作仍需核对。",
  QUOTE_RUN_ALREADY_TERMINAL: "本次报价已结束，请查看最终运行状态。",
  QUOTE_CONTINUING: "已完成验证，正在继续本次报价。",
  PROVIDER_REFERENCE_ESTIMATE: "当前金额为系统参考估价，请以平台最终报价为准。",
  PROVIDER_PENDING_REVIEW: "平台已反馈待人工审核，尚未取得最终报价。",
  AWAITING_MODEL_PARSE: "正在等待平台解析本次上传的图纸。",
  PROVIDER_VERIFICATION_REQUIRED: "平台需要人工验证，完成后点击验证并继续。",
  MANUAL_LOGIN_REQUIRED: "请在下方登录平台，然后点击验证并继续。",
  LOGIN_IDENTITY_VERIFICATION_REQUIRED: "请先完成登录及目标账号核验。",
  QUOTE_PAGE_IDENTITY_REQUIRED: "请完成报价页面的账号验证。",
  CHALLENGE_REQUIRED: "平台要求人工验证，请在下方完成后继续。",
  IDENTITY_MISMATCH: "平台当前账号与所选账号不一致，请检查账号配置。",
  ACCOUNT_CHANGED_OR_LEASE_LOST: "账号已更新或会话失效，本次报价已停止。",
  ACCOUNT_BUSY: "此账号正被其他操作占用，请稍后重试。",
  NO_AVAILABLE_ACCOUNT: "此平台没有可用账号，请先配置并启用账号。",
  ACCOUNT_SELECTION_REQUIRED: "此平台有多个可用账号，请选择本次使用的账号。",
  FILE_NOT_AUTHORIZED: "此图纸尚未授权上传至第三方平台，请先修改图纸配置。",
  CONFIG_CHANGED: "配置已更新，请使用最新配置重新发起报价。",
  PROVIDER_NOT_VERIFIED: "此平台的自动报价适配尚未通过验证，无法继续自动操作。",
  QUOTE_ADAPTER_UNVERIFIED: "此平台自动上传和报价尚未完成验证，本次运行已停止。",
  PARAMETER_MISMATCH: "平台回读参数与本次配置不一致，无法确认报价。",
  UNKNOWN_PARAMETER: "配置中有平台暂不支持的加工参数，请核对配置。",
  MUTATION_UNCONFIRMED: "平台操作回执尚未确认，已停止重复发送，请核对平台状态。",
  UPLOAD_RECEIPT_UNCONFIRMED_NO_RETRY: "图纸上传或解析结果尚未确认，未重复上传，请核对平台状态。",
  QUOTE_STAGE_TIMEOUT_NO_RETRY: "平台处理超时，操作结果尚未确认，未重复发送，请核对平台状态。",
  RUN_INTERRUPTED: "服务重启后本次操作尚待核对，未重复提交。",
  SESSION_IDLE_EXPIRED: "长时间未操作，报价会话已关闭。",
  SESSION_LIFETIME_EXPIRED: "报价会话已过期，请重新发起。",
  policy_blocked: "平台访问未通过安全检查，请检查网络或平台配置。",
  browser_dependency_missing: "报价服务缺少浏览器依赖，请联系管理员。",
  browser_capacity: "浏览器数量已达上限，请稍后重试。",
  parameters_mismatch: "平台回读参数与本次配置不一致，无法确认报价。",
  file_invalid: "图纸文件无法通过校验，请检查文件格式和内容。",
  mutation_uncertain: "平台操作回执尚未确认，已停止重复发送，请核对平台状态。",
  identity_mismatch: "平台当前账号与所选账号不一致，请检查账号配置。",
  authentication_required: "请先完成登录及目标账号核验。",
  human_challenge: "平台要求人工验证，请在下方完成后继续。",
  geometry_invalid: "平台未返回可确认的模型尺寸，无法确认本次图纸报价。",
  quote_invalid: "平台返回的价格、交期或本次报价依据未通过核验，无法确认报价。",
  intent_store_unavailable: "平台操作记录未能保存，已停止继续发送，请核对运行状态。",
  intent_conflict: "平台操作记录与本次配置不一致，已停止继续发送，请核对运行状态。",
};

export function quoteReasonMessage(reason: unknown): string | undefined {
  return typeof reason === "string" && Object.prototype.hasOwnProperty.call(reasons, reason)
    ? reasons[reason]
    : undefined;
}

/** HTTP failures are Error/HttpError; rejected business responses carry data.msg. */
export function quoteErrorMessage(failure: unknown, fallback: string): string {
  if (failure instanceof Error) return quoteReasonMessage(failure.message) || fallback;
  if (typeof failure === "object" && failure !== null && "data" in failure) {
    const envelope = failure.data;
    if (typeof envelope === "object" && envelope !== null && "msg" in envelope)
      return quoteReasonMessage(envelope.msg) || fallback;
  }
  return fallback;
}
