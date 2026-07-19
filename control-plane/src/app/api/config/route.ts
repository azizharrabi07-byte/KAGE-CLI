import { getAllConfig, setManyConfig, DEFAULT_CONFIG } from "@/lib/config";
import { logEvent } from "@/lib/observability";

export const dynamic = "force-dynamic";

export async function GET() {
  const stored = await getAllConfig();
  const merged = { ...DEFAULT_CONFIG, ...stored };
  return Response.json({ status: "ok", data: merged });
}

export async function PUT(req: Request) {
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;
  if (!body || typeof body !== "object") {
    return Response.json({ status: "error", data: null, error: "expected a JSON object" }, { status: 400 });
  }
  await setManyConfig(body);
  await logEvent({ level: "info", source: "config", message: "configuration updated", meta: { keys: Object.keys(body) } });
  const merged = { ...DEFAULT_CONFIG, ...(await getAllConfig()) };
  return Response.json({ status: "ok", data: merged });
}
