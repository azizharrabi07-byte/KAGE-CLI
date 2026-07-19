import { promises as fs } from "node:fs";
import path from "node:path";
import os from "node:os";
import { db } from "@/db";
import { logs, metrics, traces } from "@/db/schema";
import type { LogLevel, MetricKind, TraceSpan } from "@/lib/types";

/**
 * Phase 6 — Structured logging, metrics and traces.
 * - Logs are written as JSON lines to ~/.kage/logs/kage.log AND persisted to the
 *   `logs` table so the control plane can render them.
 * - All helpers swallow their own errors so observability never breaks a request.
 */

const LOG_DIR = path.join(os.homedir(), ".kage", "logs");
const LOG_FILE = path.join(LOG_DIR, "kage.log");

async function appendLogLine(line: string): Promise<void> {
  try {
    await fs.mkdir(LOG_DIR, { recursive: true });
    await fs.appendFile(LOG_FILE, `${line}\n`, "utf8");
  } catch {
    // best-effort; never throw from logging
  }
}

export interface LogPayload {
  level?: LogLevel;
  source: string;
  message: string;
  meta?: Record<string, unknown>;
}

export async function logEvent(payload: LogPayload): Promise<void> {
  const level = payload.level ?? "info";
  const record = {
    ts: new Date().toISOString(),
    level,
    source: payload.source,
    message: payload.message,
    meta: payload.meta ?? {},
  };
  // Secrets must never be logged: scrub the JSON before writing.
  const safe = scrubSecrets(JSON.stringify(record));
  await appendLogLine(safe);
  try {
    await db.insert(logs).values({
      level,
      source: payload.source,
      message: payload.message,
      meta: payload.meta ?? {},
    });
  } catch {
    // ignore DB write failure
  }
}

const SECRET_PATTERNS = [
  /(?:sk-|tok_?|api[_-]?key)["':=\s]*[A-Za-z0-9_\-]{8,}/gi,
  /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g,
];

function scrubSecrets(text: string): string {
  let out = text;
  for (const re of SECRET_PATTERNS) out = out.replace(re, "[REDACTED]");
  return out;
}

export interface MetricPayload {
  kind: MetricKind;
  value: number;
  unit?: string;
  source?: string | null;
  meta?: Record<string, unknown>;
}

export async function recordMetric(payload: MetricPayload): Promise<void> {
  try {
    await db.insert(metrics).values({
      kind: payload.kind,
      value: payload.value,
      unit: payload.unit ?? "count",
      source: payload.source ?? null,
      meta: payload.meta ?? {},
    });
  } catch {
    // ignore
  }
}

export async function addTrace(span: TraceSpan): Promise<void> {
  try {
    await db.insert(traces).values({
      agentId: span.agentId,
      parentTraceId: span.parentTraceId,
      action: span.action,
      decision: span.decision ?? null,
      input: span.input ?? null,
      output: span.output ?? null,
      durationMs: span.durationMs ?? null,
    });
  } catch {
    // ignore
  }
}
