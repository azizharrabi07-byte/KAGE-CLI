import { db } from "@/db";
import { agents, integrations, workflows, logs, metrics } from "@/db/schema";
import { sql } from "drizzle-orm";
import { ensureConfigSeeded } from "@/lib/config";
import { logEvent, recordMetric } from "@/lib/observability";
import type { WorkflowDefinition } from "@/lib/types";

/**
 * Phase 3/5 — idempotent seed so a fresh control plane has realistic agents,
 * integrations, configuration and example workflows on first boot.
 */

const DEFAULT_AGENTS = [
  { name: "Kage-Discord", kind: "discord" as const, role: "primary", provider: "openai", model: "gpt-4o-mini", description: "Primary conversational agent exposed through Discord slash commands." },
  { name: "Kage-Telegram", kind: "telegram" as const, role: "primary", provider: "openai", model: "gpt-4o-mini", description: "Mirror agent bridging the supervisor to Telegram." },
  { name: "WhatsApp-Bridge", kind: "whatsapp" as const, role: "worker", provider: "openai", model: "gpt-4o-mini", description: "Placeholder WhatsApp adapter (session-scoped)." },
  { name: "Obsidian-Curator", kind: "obsidian" as const, role: "worker", provider: "openai", model: "gpt-4o-mini", description: "Reads and writes notes to the configured Obsidian vault." },
  { name: "System-Watcher", kind: "system" as const, role: "worker", provider: "local", model: "kage-internal", description: "Health, scheduling and housekeeping for the supervisor." },
  { name: "Meta-Orchestrator", kind: "meta" as const, role: "orchestrator", provider: "openai", model: "gpt-4o", description: "Plans and delegates work across the crew of agents." },
  { name: "Browser-Scout", kind: "browser" as const, role: "worker", provider: "openai", model: "gpt-4o-mini", description: "Headless browsing, fetching and page extraction." },
  { name: "Shell-Runner", kind: "shell" as const, role: "worker", provider: "local", model: "kage-internal", description: "Sandboxed command execution within /tmp/kage-sandbox." },
  { name: "Memory-Keeper", kind: "memory" as const, role: "worker", provider: "local", model: "kage-internal", description: "Long-term recall and vector adjacency store." },
  { name: "Crew-Dispatch", kind: "crew" as const, role: "worker", provider: "openai", model: "gpt-4o", description: "Multi-agent delegation coordinator." },
];

const DEFAULT_INTEGRATIONS = [
  { name: "Discord Gateway", kind: "discord" as const, config: { token: "" }, autoReconnect: true },
  { name: "Telegram Bot API", kind: "telegram" as const, config: { botToken: "" }, autoReconnect: true },
  { name: "WhatsApp Cloud", kind: "whatsapp" as const, config: { sessionId: "", token: "" }, autoReconnect: true },
  { name: "Obsidian Vault", kind: "obsidian" as const, config: { vaultPath: "~/vault" }, autoReconnect: false },
  { name: "OpenAI Provider", kind: "llm-provider" as const, config: { provider: "openai", apiKey: "" }, autoReconnect: true },
  { name: "Postgres Store", kind: "postgres" as const, config: { url: "local" }, autoReconnect: true },
];

const onboardingWorkflow: WorkflowDefinition = {
  entryStepId: "recall",
  steps: [
    { id: "recall", name: "Recall user context", agent: "memory", action: "memory.recall", input: { seed: "onboarding" } },
    {
      id: "decide",
      name: "Compose greeting",
      agent: "discord",
      action: "llm.complete",
      input: { seed: "greeting" },
      branch: { field: "status", equals: "ok", thenStepId: "send", elseStepId: "fallback" },
      retry: { maxAttempts: 3, baseDelayMs: 100, backoffFactor: 2 },
    },
    { id: "send", name: "Post to Discord", agent: "discord", action: "discord.send", input: { channel: "general" }, next: null },
    { id: "fallback", name: "Fallback note", agent: "obsidian", action: "obsidian.write", input: { seed: "fallback" }, next: null },
  ],
};

const retryDemoWorkflow: WorkflowDefinition = {
  entryStepId: "flaky",
  steps: [
    {
      id: "flaky",
      name: "Flaky external call",
      agent: "browser",
      action: "browser.navigate",
      input: { seed: "flaky", url: "https://example.com", failTimes: 2 },
      retry: { maxAttempts: 4, baseDelayMs: 80, backoffFactor: 2 },
    },
    { id: "persist", name: "Persist result", agent: "obsidian", action: "obsidian.write", input: { seed: "persisted" } },
  ],
};

export async function ensureSeeded(): Promise<void> {
  await ensureConfigSeeded();

  const agentCount = await db.select({ c: sql<number>`count(*)::int` }).from(agents);
  if ((agentCount[0]?.c ?? 0) === 0) {
    await db.insert(agents).values(
      DEFAULT_AGENTS.map((a) => ({ ...a, status: "sleeping" as const })),
    );
  }

  const integrationCount = await db.select({ c: sql<number>`count(*)::int` }).from(integrations);
  if ((integrationCount[0]?.c ?? 0) === 0) {
    await db.insert(integrations).values(
      DEFAULT_INTEGRATIONS.map((i) => ({ ...i, status: "unknown" as const, enabled: true })),
    );
  }

  const workflowCount = await db.select({ c: sql<number>`count(*)::int` }).from(workflows);
  if ((workflowCount[0]?.c ?? 0) === 0) {
    await db.insert(workflows).values([
      {
        name: "Discord Onboarding",
        description: "Recall context, compose a greeting (branching) and post to Discord.",
        status: "draft",
        triggeredBy: "manual",
        definition: onboardingWorkflow,
        state: { results: {}, visited: [], elapsedMs: 0, startedAt: null, finishedAt: null },
      },
      {
        name: "Retry & Backoff Demo",
        description: "A flaky step that fails twice then succeeds, exercising per-step retry.",
        status: "draft",
        triggeredBy: "manual",
        definition: retryDemoWorkflow,
        state: { results: {}, visited: [], elapsedMs: 0, startedAt: null, finishedAt: null },
      },
    ]);
  }

  const logCount = await db.select({ c: sql<number>`count(*)::int` }).from(logs);
  if ((logCount[0]?.c ?? 0) === 0) {
    await logEvent({ level: "info", source: "system", message: "KAGE OS supervisor bootstrapped", meta: { phase: "init" } });
    await logEvent({ level: "info", source: "system", message: "Registry loaded 10 agents", meta: { count: 10 } });
    await logEvent({ level: "trace", source: "meta", message: "Planner idle — awaiting trigger", meta: {} });
    await logEvent({ level: "warn", source: "integration:whatsapp", message: "session token not configured", meta: {} });
  }

  const metricCount = await db.select({ c: sql<number>`count(*)::int` }).from(metrics);
  if ((metricCount[0]?.c ?? 0) === 0) {
    await recordMetric({ kind: "agent_call", value: 12, source: "discord" });
    await recordMetric({ kind: "token_usage", value: 4820, unit: "tokens", source: "discord" });
    await recordMetric({ kind: "response_time", value: 320, unit: "ms", source: "discord" });
    await recordMetric({ kind: "tool_call", value: 7, source: "browser.navigate" });
  }
}

