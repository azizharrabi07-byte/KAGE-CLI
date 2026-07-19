import { db } from "@/db";
import { workflows } from "@/db/schema";
import { eq } from "drizzle-orm";
import { sanitizeInput } from "@/lib/runtime";
import { logEvent } from "@/lib/observability";
import type { WorkflowDefinition, WorkflowStatus } from "@/lib/types";

export const dynamic = "force-dynamic";

const ALLOWED_STATUS: WorkflowStatus[] = ["draft", "running", "paused", "completed", "failed", "cancelled"];

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [row] = await db.select().from(workflows).where(eq(workflows.id, id));
  if (!row) return Response.json({ status: "error", data: null, error: "not found" }, { status: 404 });
  return Response.json({ status: "ok", data: row });
}

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [row] = await db.select().from(workflows).where(eq(workflows.id, id));
  if (!row) return Response.json({ status: "error", data: null, error: "not found" }, { status: 404 });
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;

  const patch: Record<string, unknown> = { updatedAt: new Date() };
  if (typeof body.name === "string") patch.name = sanitizeInput(body.name).slice(0, 120);
  if (typeof body.description === "string") patch.description = sanitizeInput(body.description).slice(0, 400);
  if (body.definition && Array.isArray((body.definition as WorkflowDefinition).steps)) patch.definition = body.definition;
  if (typeof body.status === "string" && ALLOWED_STATUS.includes(body.status as WorkflowStatus)) {
    patch.status = body.status as WorkflowStatus;
  }
  // convenience aliases
  if (body.cancel === true) patch.status = "cancelled";
  if (body.pause === true) patch.status = "paused";
  if (body.reset === true) {
    patch.status = "draft";
    patch.state = { results: {}, visited: [], elapsedMs: 0, startedAt: null, finishedAt: null };
    patch.currentStepId = null;
    patch.attemptCount = 0;
  }

  const [updated] = await db.update(workflows).set(patch).where(eq(workflows.id, id)).returning();
  await logEvent({ level: "info", source: "workflow", message: `workflow patched -> ${patch.status ?? "fields"}`, meta: { id } });
  return Response.json({ status: "ok", data: updated });
}

export async function DELETE(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [row] = await db.select().from(workflows).where(eq(workflows.id, id));
  if (!row) return Response.json({ status: "error", data: null, error: "not found" }, { status: 404 });
  await db.delete(workflows).where(eq(workflows.id, id));
  await logEvent({ level: "warn", source: "workflow", message: `workflow deleted: ${row.name}`, meta: { id } });
  return Response.json({ status: "ok", data: { id } });
}
