"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, SectionHeader, StatusBadge, Pill, EmptyState } from "@/components/ui";
import { relativeTime, formatMs } from "@/lib/format";
import type { WorkflowDefinition, WorkflowState } from "@/lib/types";

type Workflow = {
  id: string;
  name: string;
  description: string | null;
  status: string;
  definition: WorkflowDefinition;
  state: WorkflowState;
  currentStepId: string | null;
  attemptCount: number;
  triggeredBy: string | null;
  updatedAt: string;
};

const TEMPLATE = JSON.stringify(
  {
    name: "New Workflow",
    description: "Describe what this workflow does.",
    definition: {
      entryStepId: "s1",
      steps: [
        { id: "s1", name: "Recall context", agent: "memory", action: "memory.recall", retry: { maxAttempts: 2, baseDelayMs: 100 } },
        { id: "s2", name: "Compose", agent: "discord", action: "llm.complete", branch: { field: "status", equals: "ok", thenStepId: "s3" } },
        { id: "s3", name: "Deliver", agent: "discord", action: "discord.send" },
      ],
    },
  },
  null,
  2,
);

const ACTIONS = ["memory.recall", "browser.navigate", "llm.complete", "discord.send", "obsidian.write", "crew.delegate", "shell.exec"];

export default function WorkflowsPage() {
  const [items, setItems] = useState<Workflow[]>([]);
  const [selected, setSelected] = useState<Workflow | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [json, setJson] = useState(TEMPLATE);
  const [jsonError, setJsonError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const res = await fetch("/api/workflows", { cache: "no-store" });
    const j = await res.json();
    setItems(j.data ?? []);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const pick = useCallback(async (w: Workflow) => {
    setSelected(w);
  }, []);

  const refreshSelected = useCallback(async (id: string) => {
    const r = await fetch(`/api/workflows/${id}`, { cache: "no-store" });
    const j = await r.json();
    setSelected(j.data);
  }, []);

  const run = useCallback(
    async (w: Workflow, mode: "step" | "complete") => {
      setBusy(w.id);
      await fetch(`/api/workflows/${w.id}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      await load();
      await refreshSelected(w.id);
      setBusy(null);
    },
    [load, refreshSelected],
  );

  const patch = useCallback(
    async (w: Workflow, body: Record<string, unknown>) => {
      setBusy(w.id);
      await fetch(`/api/workflows/${w.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      await load();
      await refreshSelected(w.id);
      setBusy(null);
    },
    [load, refreshSelected],
  );

  const create = useCallback(async () => {
    setJsonError(null);
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(json);
    } catch {
      setJsonError("Invalid JSON");
      return;
    }
    const res = await fetch("/api/workflows", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed),
    });
    const j = await res.json();
    if (j.status !== "ok") {
      setJsonError(j.error ?? "creation failed");
      return;
    }
    await load();
  }, [json, load]);

  return (
    <div className="space-y-6">
      <SectionHeader title="Workflow Engine" subtitle="Conditional branching, per-step retry + backoff, resumable persistence" icon="⇄" action={<Pill tone="violet">{items.length} workflows</Pill>} />

      <Card>
        <SectionHeader title="Compose workflow" subtitle="Define steps as JSON — branching, retries and timeouts" icon="✎" />
        <textarea className="k-input mono mt-3 h-56 resize-y text-[11px] leading-relaxed" value={json} onChange={(e) => setJson(e.target.value)} spellCheck={false} />
        <div className="mt-2 flex items-center gap-2">
          <button className="k-btn k-btn-primary" onClick={create}>Create workflow</button>
          <button className="k-btn" onClick={() => setJson(TEMPLATE)}>Reset template</button>
          {jsonError && <span className="text-xs text-[var(--kage-rose)]">{jsonError}</span>}
        </div>
        <p className="mono mt-2 text-[10px] text-[var(--kage-muted)]">actions: {ACTIONS.join(" · ")}</p>
      </Card>

      <div className="grid gap-5 lg:grid-cols-5">
        <div className="space-y-2.5 lg:col-span-2">
          {loading && <EmptyState title="Loading workflows…" />}
          {!loading && items.length === 0 && <EmptyState icon="⇄" title="No workflows" hint="Create one above." />}
          {items.map((w) => (
            <button
              key={w.id}
              onClick={() => pick(w)}
              className={`k-inset k-card-hover w-full px-4 py-3 text-left ${selected?.id === w.id ? "border-violet-500/50" : ""}`}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-sm font-semibold text-white">{w.name}</p>
                <StatusBadge status={w.status} live={w.status === "running"} />
              </div>
              <p className="mt-1 line-clamp-2 text-xs text-[var(--kage-muted)]">{w.description ?? "—"}</p>
              <div className="mono mt-2 flex items-center gap-2 text-[10px] text-[var(--kage-muted)]">
                <span>{w.definition.steps.length} steps</span>·<span>{w.attemptCount} attempts</span>·<span>{relativeTime(w.updatedAt)}</span>
              </div>
            </button>
          ))}
        </div>

        <div className="lg:col-span-3">
          {selected ? <WorkflowDetail w={selected} busy={busy === selected.id} onRun={run} onPatch={patch} /> : <EmptyState icon="⇄" title="Select a workflow" hint="Step graph and run controls appear here." />}
        </div>
      </div>
    </div>
  );
}

function WorkflowDetail({
  w,
  busy,
  onRun,
  onPatch,
}: {
  w: Workflow;
  busy: boolean;
  onRun: (w: Workflow, mode: "step" | "complete") => void;
  onPatch: (w: Workflow, body: Record<string, unknown>) => void;
}) {
  const def = w.definition;
  const state = w.state ?? { results: {}, visited: [], elapsedMs: 0, startedAt: null, finishedAt: null };
  const terminal = ["completed", "failed", "cancelled"].includes(w.status);

  return (
    <Card>
      <SectionHeader title={w.name} subtitle={w.description ?? "—"} icon="⇄" action={<StatusBadge status={w.status} live={w.status === "running"} />} />

      <div className="mt-4 flex flex-wrap gap-1.5">
        <button className="k-btn k-btn-primary" disabled={busy || w.status === "running"} onClick={() => onRun(w, "complete")}>{w.status === "draft" || w.status === "paused" ? "▶ Run" : "▶ Run to end"}</button>
        <button className="k-btn" disabled={busy || terminal} onClick={() => onRun(w, "step")}>Step →</button>
        <button className="k-btn" disabled={busy || w.status !== "running"} onClick={() => onPatch(w, { pause: true })}>Pause</button>
        <button className="k-btn text-[var(--kage-rose)]" disabled={busy || terminal} onClick={() => onPatch(w, { cancel: true })}>Cancel</button>
        <button className="k-btn ml-auto" disabled={busy} onClick={() => onPatch(w, { reset: true })}>Reset</button>
      </div>

      <div className="mono mt-3 flex gap-3 text-[11px] text-[var(--kage-muted)]">
        <span>elapsed {formatMs(state.elapsedMs)}</span>·<span>{w.attemptCount} attempts</span>·<span>current: {w.currentStepId ?? "—"}</span>·<span>trigger: {w.triggeredBy}</span>
      </div>

      <p className="mt-5 mb-2 text-xs uppercase tracking-wider text-[var(--kage-muted)]">Execution graph</p>
      <div className="relative space-y-2.5">
        {def.steps.map((step, i) => {
          const result = state.results?.[step.id];
          const isCurrent = w.currentStepId === step.id;
          const tone = result?.status === "ok" ? "#34d399" : result?.status === "error" ? "#fb7185" : isCurrent ? "#60a5fa" : "#6b7280";
          return (
            <div key={step.id}>
              <div className="k-inset px-3.5 py-2.5" style={isCurrent ? { borderColor: "rgba(96,165,250,0.6)" } : undefined}>
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="mono flex h-6 w-6 items-center justify-center rounded-md text-[11px]" style={{ background: `${tone}22`, color: tone }}>{i + 1}</span>
                    <div>
                      <p className="text-sm font-medium text-white">{step.name}</p>
                      <p className="mono text-[10px] text-[var(--kage-muted)]">{step.agent} · {step.action}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {result && <span className="mono text-[10px]" style={{ color: tone }}>{result.status} · {result.attempts}x</span>}
                    {isCurrent && <span className="k-live text-[10px] text-[var(--kage-blue)]">running</span>}
                  </div>
                </div>
                <div className="mono mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-[var(--kage-muted)]">
                  {step.retry && <span>↻ retry {step.retry.maxAttempts}× backoff {step.retry.baseDelayMs}ms</span>}
                  {step.branch && <span>⎇ {step.branch.field}={String(step.branch.equals ?? step.branch.contains ?? "?")} → {step.branch.thenStepId ?? "next"} / else {step.branch.elseStepId ?? "—"}</span>}
                  {step.timeoutMs && <span>⏱ {step.timeoutMs}ms</span>}
                </div>
                {result?.output != null && (
                  <pre className="mono mt-2 max-h-24 overflow-auto rounded-md bg-black/40 p-2 text-[10px] text-[var(--kage-muted)]">{JSON.stringify(result.output, null, 0)}</pre>
                )}
              </div>
              {i < def.steps.length - 1 && <div className="ml-[18px] h-3 w-px bg-[var(--kage-border)]" />}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
