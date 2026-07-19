import { deleteConfig } from "@/lib/config";

export const dynamic = "force-dynamic";

export async function DELETE(_req: Request, { params }: { params: Promise<{ key: string }> }) {
  const { key } = await params;
  const removed = await deleteConfig(key);
  return Response.json({ status: "ok", data: { key, removed } });
}
