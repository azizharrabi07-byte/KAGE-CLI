import { db } from "@/db";
import { config } from "@/db/schema";
import { sql, eq } from "drizzle-orm";

/** Phase 3 — persistent key/value configuration store backing the wizard. */

export async function getAllConfig(): Promise<Record<string, unknown>> {
  const rows = await db.select().from(config);
  const out: Record<string, unknown> = {};
  for (const row of rows) out[row.key] = row.value;
  return out;
}

export async function getConfigValue<T>(key: string, fallback: T): Promise<T> {
  const [row] = await db.select().from(config).where(eq(config.key, key));
  return row ? (row.value as T) : fallback;
}

export async function setConfig(key: string, value: unknown): Promise<void> {
  await db
    .insert(config)
    .values({ key, value })
    .onConflictDoUpdate({ target: config.key, set: { value, updatedAt: new Date() } });
}

export async function setManyConfig(entries: Record<string, unknown>): Promise<void> {
  for (const [key, value] of Object.entries(entries)) {
    await db
      .insert(config)
      .values({ key, value })
      .onConflictDoUpdate({ target: config.key, set: { value, updatedAt: new Date() } });
  }
}

export async function deleteConfig(key: string): Promise<boolean> {
  const deleted = await db.delete(config).where(eq(config.key, key)).returning();
  return deleted.length > 0;
}

export const DEFAULT_CONFIG: Record<string, unknown> = {
  defaultProvider: "openai",
  defaultModel: "gpt-4o-mini",
  cacheTtlMs: 60000,
  logLevel: "info",
  sandboxEnabled: true,
  autoReconnect: true,
  maxConcurrency: 4,
  outputFormat: "text", // text | json | yaml
};

export async function ensureConfigSeeded(): Promise<void> {
  const count = await db.select({ c: sql<number>`count(*)` }).from(config);
  if ((count[0]?.c ?? 0) > 0) return;
  await setManyConfig(DEFAULT_CONFIG);
}
