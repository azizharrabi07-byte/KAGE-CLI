import { promises as fs } from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";

/**
 * Phase 6 — Caching.
 * Two-tier cache: a fast in-memory Map and an optional JSON disk cache.
 * Used to deduplicate identical LLM responses within a configurable TTL.
 */

export interface CacheEntry<T> {
  value: T;
  expiresAt: number;
  hits: number;
}

const TTL_MS = Number(process.env.KAGE_CACHE_TTL_MS ?? 60_000);
const DISK_DIR =
  process.env.KAGE_CACHE_DIR ?? path.join(process.cwd(), ".kage-cache");
const DISK_ENABLED = (process.env.KAGE_CACHE_DISK ?? "true") !== "false";

const memory = new Map<string, CacheEntry<unknown>>();
let diskHits = 0;
let diskWrites = 0;

async function readDisk<T>(key: string): Promise<CacheEntry<T> | null> {
  if (!DISK_ENABLED) return null;
  try {
    const raw = await fs.readFile(path.join(DISK_DIR, `${key}.json`), "utf8");
    const entry = JSON.parse(raw) as CacheEntry<T>;
    if (entry.expiresAt < Date.now()) return null;
    return entry;
  } catch {
    return null;
  }
}

async function writeDisk<T>(key: string, entry: CacheEntry<T>): Promise<void> {
  if (!DISK_ENABLED) return;
  try {
    await fs.mkdir(DISK_DIR, { recursive: true });
    await fs.writeFile(
      path.join(DISK_DIR, `${key}.json`),
      JSON.stringify(entry),
      "utf8",
    );
    diskWrites++;
  } catch {
    // disk cache is best-effort
  }
}

export async function cacheGet<T>(key: string): Promise<T | null> {
  const mem = memory.get(key) as CacheEntry<T> | undefined;
  if (mem) {
    if (mem.expiresAt < Date.now()) {
      memory.delete(key);
    } else {
      mem.hits++;
      return mem.value;
    }
  }
  const disk = await readDisk<T>(key);
  if (disk) {
    diskHits++;
    memory.set(key, disk);
    return disk.value;
  }
  return null;
}

export async function cacheSet<T>(key: string, value: T, ttlMs = TTL_MS): Promise<void> {
  const entry: CacheEntry<T> = { value, expiresAt: Date.now() + ttlMs, hits: 0 };
  memory.set(key, entry);
  await writeDisk(key, entry);
}

/** Stable cache key for an LLM call (prompt + model + temperature). */
export function llmCacheKey(parts: Record<string, unknown>): string {
  const stable = JSON.stringify(parts, Object.keys(parts).sort());
  return `llm:${createHash("sha1").update(stable).digest("hex").slice(0, 16)}`;
}

export interface CacheStats {
  memoryKeys: number;
  memoryHits: number;
  diskHits: number;
  diskWrites: number;
  ttlMs: number;
  diskEnabled: boolean;
}

export function cacheStats(): CacheStats {
  let memoryHits = 0;
  for (const entry of memory.values()) memoryHits += entry.hits;
  return {
    memoryKeys: memory.size,
    memoryHits,
    diskHits,
    diskWrites,
    ttlMs: TTL_MS,
    diskEnabled: DISK_ENABLED,
  };
}

/** Best-effort wipe used by the config/tools surface. */
export async function cacheClear(): Promise<void> {
  memory.clear();
  if (!DISK_ENABLED) return;
  try {
    await fs.rm(DISK_DIR, { recursive: true, force: true });
  } catch {
    // ignore
  }
}
