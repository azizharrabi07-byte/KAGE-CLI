import { db } from "@/db";
import { agents } from "@/db/schema";
import { desc } from "drizzle-orm";
import { sanitizeInput } from "@/lib/runtime";
import { logEvent } from "@/lib/observability";
import type { AgentKind } from "@/lib/types";

export const dynamic = "force-dynamic";

const VALID_KINDS: AgentKind[] = [
  "discord", "telegram", "whatsapp", "obsidian", "system", "meta", "browser", "shell", "memory", "crew",
];

export async function GET() {
  const rows = await db.select().from(agents).orderBy(desc(agents.createdAt));
  return Response.json({ status: "ok", data: rows });
}

export async function POST(req: Request) {
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;
  const name = sanitizeInput(String(body.name ?? "")).slice(0, 80);
  const kind = String(body.kind ?? "") as AgentKind;
  if (!name) return Response.json({ status: "error", data: null, error: "name is required" }, { status: 400 });
  if (!VALID_KINDS.includes(kind)) return Response.json({ status: "error", data: null, error: `invalid kind (allowed: ${VALID_KINDS.join(", ")})` }, { status: 400 });

  const [created] = await db
    .insert(agents)
    .values({
      name,
      kind,
      role: sanitizeInput(String(body.role ?? "worker")).slice(0, 40),
      provider: sanitizeInput(String(body.provider ?? "openai")).slice(0, 40),
      model: sanitizeInput(String(body.model ?? "gpt-4o-mini")).slice(0, 60),
      description: body.description ? sanitizeInput(String(body.description)).slice(0, 400) : null,
      config: (body.config as Record<string, unknown>) ?? {},
    })
    .returning();

  await logEvent({ level: "info", source: "registry", message: `agent registered: ${name} (${kind})`, meta: { id: created.id } });
  return Response.json({ status: "ok", data: created }, { status: 201 });
}
