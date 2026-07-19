import { refreshIntegration } from "@/lib/health";

export const dynamic = "force-dynamic";

/** Phase 4 — run a single integration health check (retry + auto-reconnect). */
export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const updated = await refreshIntegration(id);
  if (!updated) return Response.json({ status: "error", data: null, error: "not found" }, { status: 404 });
  return Response.json({ status: "ok", data: updated });
}
