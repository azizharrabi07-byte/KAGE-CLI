import { db } from "@/db";
import { integrations } from "@/db/schema";
import { desc } from "drizzle-orm";
import { refreshAllIntegrations } from "@/lib/health";

export const dynamic = "force-dynamic";

export async function GET() {
  const rows = await db.select().from(integrations).orderBy(desc(integrations.createdAt));
  return Response.json({ status: "ok", data: rows });
}

/** Re-run every health check now. */
export async function POST() {
  const rows = await refreshAllIntegrations();
  return Response.json({ status: "ok", data: rows });
}
