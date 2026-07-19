// Shared domain types for KAGE OS.
// These mirror the Python dataclasses described in the KAGE-CLI spec so the
// web control plane stays compatible with the supervisor's contracts.

/* ----------------------------- Agents & tools ----------------------------- */

export type AgentKind =
  | "discord"
  | "telegram"
  | "whatsapp"
  | "obsidian"
  | "system"
  | "meta"
  | "browser"
  | "shell"
  | "memory"
  | "crew";

export type AgentStatus = "sleeping" | "awake" | "executing" | "error";

export type ProviderKind =
  | "openai"
  | "anthropic"
  | "google"
  | "mistral"
  | "local";

/** Phase 4 — every tool/integration returns this consistent envelope. */
export interface ToolResult<T = unknown> {
  status: "ok" | "error";
  data: T | null;
  error: string | null;
  durationMs?: number;
  attempts?: number;
  meta?: Record<string, unknown>;
}

/* ------------------------------- Workflows -------------------------------- */

/** A single step inside a workflow definition. */
export interface WorkflowStep {
  id: string;
  name: string;
  /** Agent kind that owns the step, or "system". */
  agent: string;
  /** Tool/action to run, e.g. browser.navigate, memory.recall. */
  action: string;
  input?: Record<string, unknown>;
  /** Phase 5 — conditional branching. */
  branch?: {
    field: "status" | "data" | "meta.code";
    equals?: unknown;
    contains?: string;
    thenStepId?: string;
    elseStepId?: string;
  };
  /** Phase 5 — per-step retry with exponential backoff. */
  retry?: {
    maxAttempts: number;
    baseDelayMs: number;
    backoffFactor?: number;
  };
  /** Seconds before a step is considered timed out. */
  timeoutMs?: number;
  /**
   * Explicit successor. `null` marks a terminal step; a string jumps to that
   * step id; when omitted the engine follows the linear step order.
   */
  next?: string | null;
}

export interface WorkflowDefinition {
  /** Ordered entry point step id. */
  entryStepId: string;
  steps: WorkflowStep[];
}

/** Mutable runtime state persisted so a workflow can resume after restart. */
export interface WorkflowState {
  /** stepId -> outcome snapshot. */
  results: Record<
    string,
    { status: "ok" | "error" | "skipped"; output: unknown; attempts: number; finishedAt: string }
  >;
  /** Ordered list of visited step ids for the decision-chain trace. */
  visited: string[];
  /** Cumulative wall-clock runtime in ms. */
  elapsedMs: number;
  startedAt: string | null;
  finishedAt: string | null;
}

export type WorkflowStatus =
  | "draft"
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "cancelled";

/* ----------------------------- Observability ------------------------------ */

export type LogLevel = "debug" | "info" | "warn" | "error" | "trace";

export type MetricKind =
  | "response_time"
  | "token_usage"
  | "agent_call"
  | "tool_call"
  | "workflow_step";

export interface TraceSpan {
  agentId: string;
  parentTraceId?: string;
  action: string;
  decision: string;
  input?: unknown;
  output?: unknown;
  durationMs?: number;
}

/* --------------------------- Integrations & secrets ----------------------- */

export type IntegrationKind =
  | "discord"
  | "telegram"
  | "whatsapp"
  | "obsidian"
  | "llm-provider"
  | "postgres";

export type IntegrationStatus = "healthy" | "degraded" | "down" | "unknown";

export interface IntegrationHealth {
  status: IntegrationStatus;
  latencyMs: number | null;
  errorMessage: string | null;
  attempts: number;
  reconnected: boolean;
}

export interface SecretRecord {
  id: string;
  key: string;
  scope: string;
  /** Masked representation, e.g. "sk-••••••4f2a". Real value never leaves env. */
  maskedValue: string;
  hint?: string | null;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
}
