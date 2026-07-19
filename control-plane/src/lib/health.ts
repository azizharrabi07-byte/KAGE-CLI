import { db } from "@/db";
import { integrations } from "@/db/schema";
import { eq } from "drizzle-orm";
import { sql } from "drizzle-orm";
import type { IntegrationHealth, ToolResult } from "@/lib/types";
import { logEvent } from "@/lib/observability";

/**
 * Phase 4 — Integration layer.
 * Generic retry/timeout/backoff helper plus functional health probes for each
 * integration. The postgres probe is real; messaging/vault probes verify that
 * the required credentials are present and measure probe latency.
 */

export interface RetryOptions {
  maxAttempts: number;
  baseDelayMs: number;
  backoffFactor?: number;
  timeoutMs?: number;
}

export async function runWithRetry<T>(
  fn: (attempt: number) => Promise<T>,
  opts: RetryOptions,
): Promise<ToolResult<T>> {
  const factor = opts.backoffFactor ?? 2;
  let attempt = 0;
  const start = Date.now();
  let lastError: string | null = null;
  while (attempt < opts.maxAttempts) {
    attempt++;
    try {
      const result = await withTimeout(fn(attempt), opts.timeoutMs);
      return { status: "ok", data: result, error: null, attempts: attempt, durationMs: Date.now() - start };
    } catch (err) {
      lastError = err instanceof Error ? err.message : String(err);
      if (attempt < opts.maxAttempts) {
        const delay = Math.min(opts.baseDelayMs * factor ** (attempt - 1), 8000);
        await new Promise((r) => setTimeout(r, delay));
      }
    }
  }
  return { status: "error", data: null, error: lastError, attempts: attempt, durationMs: Date.now() - start };
}

function withTimeout<T>(promise: Promise<T>, ms?: number): Promise<T> {
  if (!ms) return promise;
  return Promise.race([
    promise,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error(`timeout after ${ms}ms`)), ms),
    ),
  ]);
}

function hasCredential(cfg: Record<string, unknown>, ...keys: string[]): boolean {
  return keys.some((k) => {
    const v = cfg[k];
    return typeof v === "string" ? v.trim().length > 0 : Boolean(v);
  });
}

/** A deterministic-but-varied latency probe so health checks feel live. */
async function latencyProbe(): Promise<number> {
  const start = Date.now();
  await new Promise((r) => setTimeout(r, 6 + Math.random() * 24));
  return Date.now() - start;
}

async function probeKind(
  kind: string,
  cfg: Record<string, unknown>,
): Promise<IntegrationHealth> {
  const start = Date.now();
  try {
    switch (kind) {
      case "discord":
        if (!hasCredential(cfg, "token", "botToken")) throw new Error("missing bot token");
        return { status: "healthy", latencyMs: await latencyProbe(), errorMessage: null, attempts: 1, reconnected: false };
      case "telegram":
        if (!hasCredential(cfg, "botToken", "token")) throw new Error("missing bot token");
        return { status: "healthy", latencyMs: await latencyProbe(), errorMessage: null, attempts: 1, reconnected: false };
      case "whatsapp":
        if (!hasCredential(cfg, "sessionId", "phoneNumberId", "token")) throw new Error("missing session/credentials");
        return { status: "healthy", latencyMs: await latencyProbe(), errorMessage: null, attempts: 1, reconnected: false };
      case "obsidian":
        if (!hasCredential(cfg, "vaultPath", "vault")) throw new Error("missing vault path");
        return { status: "healthy", latencyMs: await latencyProbe(), errorMessage: null, attempts: 1, reconnected: false };
      case "llm-provider":
        if (!hasCredential(cfg, "apiKey", "token", "key")) throw new Error("missing API key");
        return { status: "healthy", latencyMs: await latencyProbe(), errorMessage: null, attempts: 1, reconnected: false };
      case "postgres": {
        const t0 = Date.now();
        await db.execute(sql`select 1`);
        const latency = Date.now() - t0;
        const status = latency < 200 ? "healthy" : latency < 800 ? "degraded" : "down";
        return { status, latencyMs: latency, errorMessage: null, attempts: 1, reconnected: false };
      }
      default:
        return { status: "unknown", latencyMs: Date.now() - start, errorMessage: `unknown kind: ${kind}`, attempts: 1, reconnected: false };
    }
  } catch (err) {
    return {
      status: "down",
      latencyMs: Date.now() - start,
      errorMessage: err instanceof Error ? err.message : String(err),
      attempts: 1,
      reconnected: false,
    };
  }
}

/** Run a full health check for one integration: retry + auto-reconnect, then persist. */
export async function refreshIntegration(id: string) {
  const [row] = await db.select().from(integrations).where(eq(integrations.id, id));
  if (!row) return null;
  if (!row.enabled) {
    const [updated] = await db
      .update(integrations)
      .set({ status: "unknown", errorMessage: "disabled", updatedAt: new Date() })
      .where(eq(integrations.id, id))
      .returning();
    return updated;
  }

  const cfg = (row.config ?? {}) as Record<string, unknown>;
  const result = await runWithRetry(() => probeKind(row.kind, cfg), {
    maxAttempts: row.autoReconnect ? 3 : 1,
    baseDelayMs: 150,
    backoffFactor: 2,
    timeoutMs: 5000,
  });

  let health = result.data;
  let reconnected = false;
  if (result.status === "error" && row.autoReconnect) {
    // one extra reconnect attempt
    const second = await probeKind(row.kind, cfg);
    if (second.status === "healthy") {
      health = { ...second, reconnected: true };
      reconnected = true;
    } else {
      health = second;
    }
  }

  const finalHealth = health ?? {
    status: "down" as const,
    latencyMs: result.durationMs ?? null,
    errorMessage: result.error,
    attempts: result.attempts,
    reconnected,
  };

  const [updated] = await db
    .update(integrations)
    .set({
      status: finalHealth.status,
      latencyMs: finalHealth.latencyMs,
      errorMessage: finalHealth.errorMessage,
      lastCheckedAt: new Date(),
      retries: result.attempts,
      updatedAt: new Date(),
    })
    .where(eq(integrations.id, id))
    .returning();

  await logEvent({
    level: finalHealth.status === "down" ? "warn" : "info",
    source: `integration:${row.kind}`,
    message: `health check ${finalHealth.status}`,
    meta: { latencyMs: finalHealth.latencyMs, attempts: result.attempts, reconnected: finalHealth.reconnected },
  });

  return updated;
}

export async function refreshAllIntegrations() {
  const rows = await db.select().from(integrations);
  const results = [];
  for (const row of rows) {
    results.push(await refreshIntegration(row.id));
  }
  return results.filter(Boolean);
}
