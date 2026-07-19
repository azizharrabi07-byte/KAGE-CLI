import { db } from "@/db";
import { logs } from "@/db/schema";
import { desc, eq } from "drizzle-orm";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const level = url.searchParams.get("level");
  const source = url.searchParams.get("source");
  const limit = Math.min(Number(url.searchParams.get("limit") ?? 200), 500);

  let query = db.select().from(logs).$dynamic();
  if (level) query = query.where(eq(logs.level, level as typeof logs.level.enumValues[number]));
  if (source) query = query.where(eq(logs.source, source));
  const rows = await query.orderBy(desc(logs.createdAt)).limit(limit);
  return Response.json({ status: "ok", data: rows });
}
