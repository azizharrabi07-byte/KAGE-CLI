import { listSecrets, upsertSecret, removeSecret, sanitizeInput } from "@/lib/runtime";
import { logEvent } from "@/lib/observability";

export const dynamic = "force-dynamic";

/**
 * Phase 6 — Secret management.
 * Plaintext is never persisted; only a masked reference is stored so the UI can
 * show presence and allow removal. Real resolution happens via process.env.
 */
export async function GET(req: Request) {
  const scope = new URL(req.url).searchParams.get("scope") ?? undefined;
  const data = await listSecrets(scope);
  return Response.json({ status: "ok", data });
}

export async function POST(req: Request) {
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;
  const key = sanitizeInput(String(body.key ?? "")).toUpperCase().replace(/\s+/g, "_");
  const value = String(body.value ?? "");
  if (!key || !value) return Response.json({ status: "error", data: null, error: "key and value are required" }, { status: 400 });
  const scope = sanitizeInput(String(body.scope ?? "global")).slice(0, 40);
  const data = await upsertSecret(key, value, scope);
  await logEvent({ level: "info", source: "secrets", message: `secret stored (masked): ${key}`, meta: { scope } });
  return Response.json({ status: "ok", data }, { status: 201 });
}

export async function DELETE(req: Request) {
  const url = new URL(req.url);
  const key = url.searchParams.get("key");
  if (!key) return Response.json({ status: "error", data: null, error: "key query param is required" }, { status: 400 });
  const removed = await removeSecret(key);
  await logEvent({ level: "warn", source: "secrets", message: `secret removed: ${key}`, meta: {} });
  return Response.json({ status: "ok", data: { key, removed } });
}
