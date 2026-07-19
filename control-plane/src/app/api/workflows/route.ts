import { db } from "@/db";
import { workflows } from "@/db/schema";
import { desc } from "drizzle-orm";
import { sanitizeInput } from "@/lib/runtime";
import { logEvent } from "@/lib/observability";
import type { WorkflowDefinition } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET() {
  const rows = await db.select().from(workflows).orderBy(desc(workflows.createdAt));
  return Response.json({ status: "ok", data: rows });
}

function validateDefinition(def: unknown): def is WorkflowDefinition {
  if (!def || typeof def !== "object") return false;
  const d = def as Partial<WorkflowDefinition>;
  return Array.isArray(d.steps) && typeof d.entryStepId === "string" && d.steps.length > 0;
}

export async function POST(req: Request) {
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;
  const name = sanitizeInput(String(body.name ?? "")).slice(0, 120);
  if (!name) return Response.json({ status: "error", data: null, error: "name is required" }, { status: 400 });
  if (!validateDefinition(body.definition)) {
    return Response.json({ status: "error", data: null, error: "definition must include entryStepId and a non-empty steps[]" }, { status: 400 });
  }

  const [created] = await db
    .insert(workflows)
    .values({
      name,
      description: body.description ? sanitizeInput(String(body.description)).slice(0, 400) : null,
      status: "draft",
      triggeredBy: String(body.triggeredBy ?? "manual"),
      definition: body.definition as WorkflowDefinition,
    })
    .returning();

  await logEvent({ level: "info", source: "workflow", message: `workflow created: ${name}`, meta: { id: created.id } });
  return Response.json({ status: "ok", data: created }, { status: 201 });
}
