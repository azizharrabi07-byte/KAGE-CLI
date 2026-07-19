import { db } from "@/db";
import { integrations } from "@/db/schema";
import { eq } from "drizzle-orm";
import { logEvent } from "@/lib/observability";

export const dynamic = "force-dynamic";

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [row] = await db.select().from(integrations).where(eq(integrations.id, id));
  if (!row) return Response.json({ status: "error", data: null, error: "not found" }, { status: 404 });
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;

  const patch: Record<string, unknown> = { updatedAt: new Date() };
  if (typeof body.enabled === "boolean") patch.enabled = body.enabled;
  if (typeof body.autoReconnect === "boolean") patch.autoReconnect = body.autoReconnect;
  if (typeof body.name === "string") patch.name = body.name;
  if (body.config && typeof body.config === "object") patch.config = body.config;

  const [updated] = await db.update(integrations).set(patch).where(eq(integrations.id, id)).returning();
  await logEvent({ level: "info", source: `integration:${row.kind}`, message: `integration updated`, meta: { id, patch } });
  return Response.json({ status: "ok", data: updated });
}
