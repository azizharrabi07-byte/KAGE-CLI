import {
  pgTable,
  text,
  timestamp,
  integer,
  real,
  jsonb,
  boolean,
  uuid,
  pgEnum,
  index,
} from "drizzle-orm/pg-core";
import type {
  AgentStatus,
  AgentKind,
  WorkflowDefinition,
  WorkflowState,
  WorkflowStatus,
  IntegrationKind,
  IntegrationStatus,
  LogLevel,
  MetricKind,
} from "@/lib/types";

export { sql } from "drizzle-orm";

/* --------------------------------- Agents --------------------------------- */

export const agentStatusEnum = pgEnum("agent_status", [
  "sleeping",
  "awake",
  "executing",
  "error",
]);

export const agents = pgTable(
  "agents",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    name: text("name").notNull(),
    kind: text("kind").$type<AgentKind>().notNull(),
    role: text("role").notNull().default("worker"),
    status: agentStatusEnum("status").$type<AgentStatus>().notNull().default("sleeping"),
    provider: text("provider").notNull().default("openai"),
    model: text("model").notNull().default("gpt-4o-mini"),
    description: text("description"),
    config: jsonb("config").$type<Record<string, unknown>>().notNull().default({}),
    lastActiveAt: timestamp("last_active_at", { withTimezone: true }),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("agents_status_idx").on(t.status)],
);

export type Agent = typeof agents.$inferSelect;
export type NewAgent = typeof agents.$inferInsert;

/* -------------------------------- Workflows ------------------------------- */

export const workflowStatusEnum = pgEnum("workflow_status", [
  "draft",
  "running",
  "paused",
  "completed",
  "failed",
  "cancelled",
]);

export const workflows = pgTable(
  "workflows",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    name: text("name").notNull(),
    description: text("description"),
    status: workflowStatusEnum("status").$type<WorkflowStatus>().notNull().default("draft"),
    definition: jsonb("definition").$type<WorkflowDefinition>().notNull(),
    state: jsonb("state")
      .$type<WorkflowState>()
      .notNull()
      .default({ results: {}, visited: [], elapsedMs: 0, startedAt: null, finishedAt: null }),
    currentStepId: text("current_step_id"),
    attemptCount: integer("attempt_count").notNull().default(0),
    triggeredBy: text("triggered_by").default("manual"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("workflows_status_idx").on(t.status)],
);

export type Workflow = typeof workflows.$inferSelect;
export type NewWorkflow = typeof workflows.$inferInsert;

/* ------------------------------- Integrations ----------------------------- */

export const integrationStatusEnum = pgEnum("integration_status", [
  "healthy",
  "degraded",
  "down",
  "unknown",
]);

export const integrations = pgTable(
  "integrations",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    name: text("name").notNull(),
    kind: text("kind").$type<IntegrationKind>().notNull(),
    enabled: boolean("enabled").notNull().default(true),
    status: integrationStatusEnum("status").$type<IntegrationStatus>().notNull().default("unknown"),
    latencyMs: integer("latency_ms"),
    lastCheckedAt: timestamp("last_checked_at", { withTimezone: true }),
    errorMessage: text("error_message"),
    retries: integer("retries").notNull().default(0),
    autoReconnect: boolean("auto_reconnect").notNull().default(true),
    config: jsonb("config").$type<Record<string, unknown>>().notNull().default({}),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("integrations_status_idx").on(t.status)],
);

export type Integration = typeof integrations.$inferSelect;
export type NewIntegration = typeof integrations.$inferInsert;

/* ----------------------------- Observability ------------------------------ */

export const logLevelEnum = pgEnum("log_level", [
  "debug",
  "info",
  "warn",
  "error",
  "trace",
]);

export const logs = pgTable(
  "logs",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    level: logLevelEnum("level").$type<LogLevel>().notNull().default("info"),
    source: text("source").notNull(),
    message: text("message").notNull(),
    meta: jsonb("meta").$type<Record<string, unknown>>().notNull().default({}),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [
    index("logs_created_idx").on(t.createdAt),
    index("logs_level_idx").on(t.level),
    index("logs_source_idx").on(t.source),
  ],
);

export type Log = typeof logs.$inferSelect;

export const metricKindEnum = pgEnum("metric_kind", [
  "response_time",
  "token_usage",
  "agent_call",
  "tool_call",
  "workflow_step",
]);

export const metrics = pgTable(
  "metrics",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    kind: metricKindEnum("kind").$type<MetricKind>().notNull(),
    value: real("value").notNull(),
    unit: text("unit").notNull().default("count"),
    source: text("source"),
    meta: jsonb("meta").$type<Record<string, unknown>>().notNull().default({}),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [
    index("metrics_created_idx").on(t.createdAt),
    index("metrics_kind_idx").on(t.kind),
  ],
);

export type Metric = typeof metrics.$inferSelect;

export const traces = pgTable(
  "traces",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    agentId: text("agent_id").notNull(),
    parentTraceId: uuid("parent_trace_id"),
    action: text("action").notNull(),
    decision: text("decision"),
    input: jsonb("input"),
    output: jsonb("output"),
    durationMs: integer("duration_ms"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [
    index("traces_agent_idx").on(t.agentId),
    index("traces_created_idx").on(t.createdAt),
  ],
);

export type Trace = typeof traces.$inferSelect;

/* -------------------------------- Secrets --------------------------------- */

export const secrets = pgTable(
  "secrets",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    key: text("key").notNull().unique(),
    scope: text("scope").notNull().default("global"),
    maskedValue: text("masked_value").notNull(),
    hint: text("hint"),
    enabled: boolean("enabled").notNull().default(true),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("secrets_scope_idx").on(t.scope)],
);

export type Secret = typeof secrets.$inferSelect;

/* --------------------------------- Config --------------------------------- */

export const config = pgTable("config", {
  key: text("key").primaryKey(),
  value: jsonb("value").notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export type ConfigRow = typeof config.$inferSelect;
