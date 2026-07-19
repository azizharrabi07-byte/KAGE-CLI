import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { promises as fs } from "node:fs";
import { validateShellCommand } from "@/lib/runtime";
import { logEvent } from "@/lib/observability";
import type { ToolResult } from "@/lib/types";

export const dynamic = "force-dynamic";

const execFileP = promisify(execFile);
const SANDBOX = "/tmp/kage-sandbox";

/**
 * Phase 6 — sandboxed shell tool.
 * Commands are validated against an allow-list and executed inside a temporary
 * directory with a hard timeout. `dryRun` returns the validation verdict only.
 */
export async function POST(req: Request) {
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;
  const command = String(body.command ?? "");
  const dryRun = body.dryRun === true;

  const validation = validateShellCommand(command);
  if (validation.status === "error") {
    return Response.json({
      status: "error",
      data: null,
      error: validation.error,
      meta: { stage: "validation", dryRun },
    } satisfies ToolResult);
  }

  if (dryRun) {
    await logEvent({ level: "info", source: "tool:shell", message: `dry-run ok: ${command}`, meta: { sandbox: SANDBOX } });
    return Response.json({
      status: "ok",
      data: { validation, executed: false, dryRun: true, stdout: null },
      error: null,
    } satisfies ToolResult);
  }

  await fs.mkdir(SANDBOX, { recursive: true });
  const start = Date.now();
  try {
    const { stdout } = await execFileP(validation.data!.command, validation.data!.args, {
      cwd: SANDBOX,
      timeout: 5000,
      maxBuffer: 64 * 1024,
    });
    await logEvent({ level: "info", source: "tool:shell", message: `exec ok: ${command}`, meta: { durationMs: Date.now() - start } });
    return Response.json({
      status: "ok",
      data: { validation, executed: true, stdout, durationMs: Date.now() - start },
      error: null,
    } satisfies ToolResult);
  } catch (err) {
    return Response.json({
      status: "error",
      data: null,
      error: err instanceof Error ? err.message : String(err),
      durationMs: Date.now() - start,
      meta: { stage: "exec", sandbox: SANDBOX },
    } satisfies ToolResult);
  }
}
