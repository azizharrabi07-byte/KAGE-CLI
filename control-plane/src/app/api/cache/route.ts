import { cacheStats, cacheClear } from "@/lib/cache";
import { logEvent } from "@/lib/observability";

export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json({ status: "ok", data: cacheStats() });
}

export async function DELETE() {
  await cacheClear();
  await logEvent({ level: "info", source: "cache", message: "cache cleared", meta: {} });
  return Response.json({ status: "ok", data: cacheStats() });
}
