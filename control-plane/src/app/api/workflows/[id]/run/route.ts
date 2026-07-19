import { db } from "@/db";
import { workflows } from "@/db/schema";
import { eq } from "drizzle-orm";
import { stepWorkflow, runWorkflowToCompletion } from "@/lib/workflow-engine";

export const dynamic = "force-dynamic";

/** Phase 5 — run one step (resumable) or run to completion. */
export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [row] = await db.select().from(workflows).where(eq(workflows.id, id));
  if (!row) return Response.json({ status: "error", data: null, error: "not found" }, { status: 404 });

  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;
  const mode = body.mode === "step" ? "step" : "complete";

  const result = mode === "step" ? await stepWorkflow(id) : await runWorkflowToCompletion(id);
  return Response.json({ status: "ok", data: result, mode });
}
