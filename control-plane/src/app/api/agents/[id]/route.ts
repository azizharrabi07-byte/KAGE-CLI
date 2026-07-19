import { db } from "@/db";
import { agents } from "@/db/schema";
import { eq } from "drizzle-orm";
import { logEvent, recordMetric, addTrace } from "@/lib/observability";
import type { AgentStatus } from "@/lib/types";

export const dynamic = "force-dynamic";

const DECISIONS: Record<string, string> = {
  discord: "dispatched slash-command response",
  telegram: "mirrored message to bridge",
  whatsapp: "queued outbound message",
  obsidian: "appended note to vault",
  system: "ran housekeeping sweep",
  meta: "delegated sub-task to crew",
  browser: "scraped target page",
  shell: "executed sandboxed command",
  memory: "stored vector embedding",
  crew: "fanned out to agents",
};

async function load(id: string) {
  const [row] = await db.select().from(agents).where(eq(agents.id, id));
  return row;
}

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const row = await load(id);
  if (!row) return Response.json({ status: "error", data: null, error: "not found" }, { status: 404 });
  return Response.json({ status: "ok", data: row });
}

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const row = await load(id);
  if (!row) return Response.json({ status: "error", data: null, error: "not found" }, { status: 404 });
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;

  const patch: Record<string, unknown> = { updatedAt: new Date() };
  const action = String(body.action ?? "");

  if (action === "wake") patch.status = "awake" as AgentStatus;
  else if (action === "sleep") patch.status = "sleeping" as AgentStatus;
  else if (action === "execute") patch.status = "executing" as AgentStatus;
  else if (typeof body.status === "string") patch.status = body.status as AgentStatus;

  if (typeof body.name === "string") patch.name = body.name;
  if (typeof body.provider === "string") patch.provider = body.provider;
  if (typeof body.model === "string") patch.model = body.model;
  if (typeof body.role === "string") patch.role = body.role;
  if (typeof body.description === "string") patch.description = body.description;
  if (body.config && typeof body.config === "object") patch.config = body.config;

  const [updated] = await db.update(agents).set(patch).where(eq(agents.id, id)).returning();

  if (action) {
    const decision = DECISIONS[row.kind] ?? `${action} transition`;
    await logEvent({ level: "info", source: `agent:${row.name}`, message: `${action} -> ${patch.status ?? row.status}`, meta: { agentId: id } });
    await recordMetric({ kind: "agent_call", value: 1, source: row.name });
    await addTrace({ agentId: id, action, decision, durationMs: Math.round(Math.random() * 200 + 40) });
    if (action === "execute") {
      const [settled] = await db.update(agents).set({ status: "awake", lastActiveAt: new Date(), updatedAt: new Date() }).where(eq(agents.id, id)).returning();
      return Response.json({ status: "ok", data: settled, decision });
    }
  }

  return Response.json({ status: "ok", data: updated });
}

export async function DELETE(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const row = await load(id);
  if (!row) return Response.json({ status: "error", data: null, error: "not found" }, { status: 404 });
  await db.delete(agents).where(eq(agents.id, id));
  await logEvent({ level: "warn", source: "registry", message: `agent removed: ${row.name}`, meta: { id } });
  return Response.json({ status: "ok", data: { id } });
}
