import { db } from "@/db";
import { secrets } from "@/db/schema";
import { eq } from "drizzle-orm";
import type { ToolResult, SecretRecord } from "@/lib/types";

/**
 * Phase 6 — Security runtime.
 * - Input sanitization before passing user text to shell or LLM.
 * - Sandboxed shell execution restricted to a temporary working directory.
 * - Secret management: real values live ONLY in process.env; the DB stores a
 *   masked reference so secrets are never echoed or logged.
 */

const MAX_INPUT = 4000;

/** Strip control characters, null bytes and collapse whitespace. */
export function sanitizeInput(input: string): string {
  return input
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "")
    .replace(/\r/g, "")
    .trim()
    .slice(0, MAX_INPUT);
}

const FORBIDDEN_SHELL = [
  /(\s|^|;)\s*rm\s+-rf?\s+\//,
  /:\(\)\s*\{/,
  /\b(curl|wget)\b/i,
  /\b(nc|bash|sh|zsh|dash)\b\s*-c/i,
  /\$\(/,
  /`/,
  /\b(?:mkfs|dd)\s+if=/i,
  /\bshutdown\b|\breboot\b/i,
];

const ALLOWED_COMMANDS = new Set([
  "ls", "cat", "pwd", "echo", "wc", "grep", "head", "tail",
  "date", "whoami", "uname", "stat", "file", "find", "sort", "uniq",
]);

/** Validate a shell command against an allow-list and a sandbox dir. */
export function validateShellCommand(rawCommand: string): ToolResult<{ command: string; args: string[]; sandbox: string }> {
  const command = sanitizeInput(rawCommand);
  if (!command) {
    return { status: "error", data: null, error: "empty command", attempts: 1 };
  }
  for (const pattern of FORBIDDEN_SHELL) {
    if (pattern.test(command)) {
      return {
        status: "error",
        data: null,
        error: `blocked by sandbox policy: matched ${pattern}`,
        attempts: 1,
      };
    }
  }
  const [bin, ...args] = command.split(/\s+/);
  if (!bin || !ALLOWED_COMMANDS.has(bin.toLowerCase())) {
    return {
      status: "error",
      data: null,
      error: `command '${bin ?? "?"}' is not in the allow-list`,
      attempts: 1,
    };
  }
  if (args.some((a) => a.startsWith("/") && a !== "/")) {
    return { status: "error", data: null, error: "absolute paths are not permitted in the sandbox", attempts: 1 };
  }
  return {
    status: "ok",
    data: { command: bin, args, sandbox: "/tmp/kage-sandbox" },
    error: null,
  };
}

/* -------------------------------- Secrets --------------------------------- */

export function maskSecret(value: string): { maskedValue: string; hint: string | null } {
  if (!value) return { maskedValue: "••••", hint: null };
  const visible = value.slice(-4);
  const masked = `${"•".repeat(Math.min(Math.max(value.length - 4, 4), 24))}${visible}`;
  return { maskedValue: masked, hint: `...${visible}` };
}

/** Read a secret from the environment ONLY. Returns undefined if not present. */
export function resolveSecret(key: string): string | undefined {
  return process.env[key];
}

function rowToRecord(row: typeof secrets.$inferSelect): SecretRecord {
  return {
    id: row.id,
    key: row.key,
    scope: row.scope,
    maskedValue: row.maskedValue,
    hint: row.hint,
    enabled: row.enabled,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function listSecrets(scope?: string): Promise<SecretRecord[]> {
  const rows = scope ? await db.select().from(secrets).where(eq(secrets.scope, scope)) : await db.select().from(secrets);
  return rows.map(rowToRecord).sort((a, b) => a.key.localeCompare(b.key));
}

export async function upsertSecret(key: string, value: string, scope = "global"): Promise<SecretRecord> {
  const { maskedValue, hint } = maskSecret(value);
  const existing = await db.select().from(secrets).where(eq(secrets.key, key));
  if (existing.length > 0) {
    const [updated] = await db
      .update(secrets)
      .set({ maskedValue, hint, scope, enabled: true, updatedAt: new Date() })
      .where(eq(secrets.key, key))
      .returning();
    return rowToRecord(updated);
  }
  const [created] = await db
    .insert(secrets)
    .values({ key, scope, maskedValue, hint, enabled: true })
    .returning();
  return rowToRecord(created);
}

export async function removeSecret(key: string): Promise<boolean> {
  const deleted = await db.delete(secrets).where(eq(secrets.key, key)).returning();
  return deleted.length > 0;
}
