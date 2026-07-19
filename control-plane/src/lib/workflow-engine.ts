import { db } from "@/db";
import { workflows } from "@/db/schema";
import { eq } from "drizzle-orm";
import type { WorkflowDefinition, WorkflowState, WorkflowStep, WorkflowStatus, ToolResult } from "@/lib/types";
import { runWithRetry } from "@/lib/health";
import { logEvent, recordMetric, addTrace } from "@/lib/observability";

/**
 * Phase 5 — Workflow engine.
 * Steps are executed with optional retry/backoff + timeout. After each step the
 * optional `branch` rule decides the next step; otherwise the engine follows the
 * linear step order. State is persisted to the `workflows.state` column so a run
 * can resume after a restart.
 */

export type WorkflowRow = typeof workflows.$inferSelect;

function emptyState(): WorkflowState {
  return { results: {}, visited: [], elapsedMs: 0, startedAt: null, finishedAt: null };
}

/* --------------------------- simulated actions ---------------------------- */

function actionData(action: string, input: Record<string, unknown>): unknown {
  const seed = (input.seed as string) ?? "kage";
  switch (action) {
    case "memory.recall":
      return { facts: [`note:${seed}-1`, `note:${seed}-2`], count: 2 };
    case "browser.navigate":
      return { url: input.url ?? "https://example.com", title: `${seed} page`, status: 200 };
    case "llm.complete":
      return { completion: `decision based on ${seed}`, tokens: 120 + (seed.length % 50) };
    case "discord.send":
      return { messageId: `msg_${seed}_${Date.now().toString(36)}`, channel: input.channel ?? "general" };
    case "obsidian.write":
      return { note: `${seed}.md`, bytes: 256 };
    case "crew.delegate":
      return { delegatedTo: input.agent ?? "system", accepted: true };
    case "shell.exec":
      return { stdout: `${seed}\n`, exitCode: 0 };
    default:
      return { action, ok: true };
  }
}

/**
 * Simulated step action. `failTimes` (from step.input) lets a workflow author
 * demonstrate the retry/backoff path by failing the first N attempts.
 */
async function runAction(step: WorkflowStep, attempt: number): Promise<ToolResult> {
  const input = (step.input ?? {}) as Record<string, unknown> & { failTimes?: number };
  const failTimes = typeof input.failTimes === "number" ? input.failTimes : 0;
  if (attempt <= failTimes) {
    throw new Error(`simulated transient failure (attempt ${attempt}/${failTimes})`);
  }
  const data = actionData(step.action, input);
  return { status: "ok", data, error: null, attempts: attempt };
}

/* --------------------------- branching helpers ---------------------------- */

type BranchField = "status" | "data" | "meta.code";

function getFieldValue(result: ToolResult, field: BranchField): unknown {
  if (field === "status") return result.status;
  if (field === "data") return result.data;
  if (field === "meta.code") return (result.meta as Record<string, unknown> | undefined)?.code;
  return undefined;
}

function evaluateBranch(result: ToolResult, branch: NonNullable<WorkflowStep["branch"]>): string | null {
  const value = getFieldValue(result, branch.field);
  let matched = false;
  if (branch.equals !== undefined) matched = value === branch.equals;
  else if (branch.contains !== undefined && typeof value === "string") matched = value.includes(branch.contains);
  else if (branch.contains !== undefined && value !== null && value !== undefined) matched = String(value).includes(branch.contains);
  return matched ? branch.thenStepId ?? null : branch.elseStepId ?? null;
}

function nextInOrder(def: WorkflowDefinition, stepId: string): string | null {
  const idx = def.steps.findIndex((s) => s.id === stepId);
  if (idx === -1) return null;
  return def.steps[idx + 1]?.id ?? null;
}

/** Resolve the next step when no branch rule applies: explicit `next`, else linear. */
function resolveDefaultNext(step: WorkflowStep, def: WorkflowDefinition): string | null {
  if (step.next === null) return null;
  if (typeof step.next === "string") return step.next;
  return nextInOrder(def, step.id);
}

function findStep(def: WorkflowDefinition, stepId: string | null): WorkflowStep | null {
  if (!stepId) return null;
  return def.steps.find((s) => s.id === stepId) ?? null;
}

/* ------------------------------- execution -------------------------------- */

export async function setWorkflowStatus(id: string, status: WorkflowStatus) {
  const patch: Record<string, unknown> = { status, updatedAt: new Date() };
  const statePatch: Partial<WorkflowState> = {};
  if (status === "completed" || status === "failed" || status === "cancelled") {
    statePatch.finishedAt = new Date().toISOString();
  }
  const [row] = await db.select().from(workflows).where(eq(workflows.id, id));
  if (!row) return null;
  const mergedState = { ...(row.state as WorkflowState), ...statePatch };
  patch.state = mergedState;
  const [updated] = await db
    .update(workflows)
    .set(patch)
    .where(eq(workflows.id, id))
    .returning();
  await logEvent({
    level: status === "failed" || status === "cancelled" ? "warn" : "info",
    source: `workflow:${row.name}`,
    message: `status -> ${status}`,
    meta: { workflowId: id },
  });
  return updated;
}

/** Advance a workflow by exactly one step and persist the new state. */
export async function stepWorkflow(id: string): Promise<WorkflowRow | null> {
  const [row] = await db.select().from(workflows).where(eq(workflows.id, id));
  if (!row) return null;
  if (row.status === "completed" || row.status === "failed" || row.status === "cancelled") {
    return row;
  }

  const def = row.definition as WorkflowDefinition;
  const state = (row.state as WorkflowState) ?? emptyState();
  if (!state.startedAt) state.startedAt = new Date().toISOString();
  if (!state.results) state.results = {};
  if (!state.visited) state.visited = [];

  // resolve current step: explicit pointer, else the entry step.
  let currentStepId = row.currentStepId;
  let step: WorkflowStep | null = currentStepId ? findStep(def, currentStepId) : null;
  if (!step) {
    step = findStep(def, def.entryStepId);
    currentStepId = def.entryStepId;
  }
  if (!step) {
    // nothing to run -> mark complete
    state.finishedAt = new Date().toISOString();
    await db.update(workflows).set({ status: "completed", state, currentStepId: null, updatedAt: new Date() }).where(eq(workflows.id, id));
    return (await db.select().from(workflows).where(eq(workflows.id, id)))[0];
  }

  const stepStart = Date.now();
  const retry = step.retry ?? { maxAttempts: 1, baseDelayMs: 0 };
  const result = await runWithRetry((attempt) => runAction(step!, attempt), {
    maxAttempts: retry.maxAttempts,
    baseDelayMs: retry.baseDelayMs,
    backoffFactor: retry.backoffFactor ?? 2,
    timeoutMs: step.timeoutMs ?? 5000,
  });

  const elapsed = Date.now() - stepStart;
  state.elapsedMs += elapsed;
  state.results[step.id] = {
    status: result.status,
    output: result.data,
    attempts: result.attempts ?? 1,
    finishedAt: new Date().toISOString(),
  };
  if (!state.visited.includes(step.id)) state.visited.push(step.id);

  // branching
  let nextStepId: string | null;
  if (result.status === "error") {
    nextStepId = null;
    state.finishedAt = new Date().toISOString();
  } else if (step.branch) {
    nextStepId = evaluateBranch(result, step.branch) ?? resolveDefaultNext(step, def);
  } else {
    nextStepId = resolveDefaultNext(step, def);
  }
  if (!nextStepId) state.finishedAt = new Date().toISOString();

  const status: WorkflowStatus = result.status === "error" ? "failed" : nextStepId ? "running" : "completed";
  await db
    .update(workflows)
    .set({ status, state, currentStepId: nextStepId, attemptCount: row.attemptCount + (result.attempts ?? 1), updatedAt: new Date() })
    .where(eq(workflows.id, id));

  // observability
  const actionName = step.action;
  await logEvent({
    level: result.status === "error" ? "error" : "info",
    source: `workflow:${row.name}`,
    message: `step '${step.name}' -> ${result.status}`,
    meta: { stepId: step.id, attempts: result.attempts, elapsedMs: elapsed, next: nextStepId },
  });
  await recordMetric({ kind: "workflow_step", value: 1, source: row.name, meta: { step: step.id, status: result.status } });
  await recordMetric({ kind: "response_time", value: elapsed, unit: "ms", source: row.name });
  await recordMetric({ kind: "agent_call", value: 1, source: step.agent });
  await recordMetric({ kind: "tool_call", value: 1, source: step.action });
  if (actionName === "llm.complete" && result.data && typeof result.data === "object" && "tokens" in result.data) {
    const tokens = Number((result.data as { tokens: number }).tokens);
    await recordMetric({ kind: "token_usage", value: tokens, unit: "tokens", source: row.name });
  }
  await addTrace({
    agentId: step.agent,
    action: step.action,
    decision: nextStepId ? `advance -> ${nextStepId}` : status,
    input: step.input,
    output: result.data,
    durationMs: elapsed,
  });

  const [updated] = await db.select().from(workflows).where(eq(workflows.id, id));
  return updated;
}

/** Advance a workflow until it reaches a terminal state (or a configured cap). */
export async function runWorkflowToCompletion(id: string, maxSteps = 50): Promise<WorkflowRow | null> {
  let current = await setWorkflowStatus(id, "running");
  let guard = 0;
  while (current && (current.status === "running" || current.status === "paused" || current.status === "draft") && guard < maxSteps) {
    current = await stepWorkflow(id);
    guard++;
  }
  return current;
}
