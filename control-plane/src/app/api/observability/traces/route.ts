import { db } from "@/db";
import { traces } from "@/db/schema";
import { desc, eq } from "drizzle-orm";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const limit = Math.min(Number(url.searchParams.get("limit") ?? 100), 500);
  const agentId = url.searchParams.get("agentId");
  let query = db.select().from(traces).$dynamic();
  if (agentId) query = query.where(eq(traces.agentId, agentId));
  const rows = await query.orderBy(desc(traces.createdAt)).limit(limit);
  return Response.json({ status: "ok", data: rows });
}
