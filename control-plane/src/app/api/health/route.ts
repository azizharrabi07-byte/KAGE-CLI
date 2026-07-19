import { db } from "@/db";
import { sql } from "drizzle-orm";
import { VERSION, CODENAME } from "@/lib/version";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    await db.execute(sql`select 1`);
    return Response.json({
      ok: true,
      service: "kage-os",
      version: VERSION,
      codename: CODENAME,
    });
  } catch (err) {
    return Response.json(
      {
        ok: false,
        error: err instanceof Error ? err.message : "database unreachable",
      },
      { status: 500 },
    );
  }
}
