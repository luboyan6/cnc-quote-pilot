const eventTypes = new Set([
  "turn.started",
  "text.delta",
  "skill.activated",
  "tool.started",
  "tool.completed",
  "tool.failed",
  "domain.progress",
  "evidence.available",
  "turn.completed",
  "turn.stopped",
  "turn.failed",
] as const);

export type AgentEventType = typeof eventTypes extends Set<infer T> ? T : never;

export interface AgentEvent {
  session_id: string;
  turn_id: string;
  seq: number;
  type: AgentEventType;
  payload: Record<string, unknown>;
}

export type ChatWireEvent = AgentEvent | { type: "request.error"; payload: { code: string } };

export function decodeChatEvent(raw: string): ChatWireEvent | null {
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const data = value as Record<string, unknown>;
  if (!data.payload || typeof data.payload !== "object" || Array.isArray(data.payload)) return null;
  const payload = data.payload as Record<string, unknown>;
  if (data.type === "request.error") {
    return typeof payload.code === "string"
      ? { type: "request.error", payload: { code: payload.code } }
      : null;
  }
  if (
    typeof data.type !== "string" ||
    !eventTypes.has(data.type as AgentEventType) ||
    typeof data.session_id !== "string" ||
    typeof data.turn_id !== "string" ||
    !Number.isSafeInteger(data.seq) ||
    (data.seq as number) < 1
  )
    return null;
  return {
    type: data.type as AgentEventType,
    session_id: data.session_id,
    turn_id: data.turn_id,
    seq: data.seq as number,
    payload,
  };
}
