"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, SectionHeader, StatusBadge, Pill, EmptyState } from "@/components/ui";
import { relativeTime } from "@/lib/format";

type Agent = {
  id: string;
  name: string;
  kind: string;
  role: string;
  status: string;
  provider: string;
  model: string;
  description: string | null;
  config: Record<string, unknown>;
  lastActiveAt: string | null;
  createdAt: string;
};

type Trace = {
  id: string;
  action: string;
  decision: string | null;
  durationMs: number | null;
  createdAt: string;
  output: unknown;
};

const KINDS = ["discord", "telegram", "whatsapp", "obsidian", "system", "meta", "browser", "shell", "memory", "crew"];

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selected, setSelected] = useState<Agent | null>(null);
  const [traces, setTraces] = useState<Trace[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState({ name: "", kind: "discord", model: "gpt-4o-mini", provider: "openai", description: "" });

  const load = useCallback(async () => {
    const res = await fetch("/api/agents", { cache: "no-store" });
    const json = await res.json();
    setAgents(json.data ?? []);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const select = useCallback(async (a: Agent) => {
    setSelected(a);
    const res = await fetch(`/api/observability/traces?agentId=${a.id}&limit=12`, { cache: "no-store" });
    const json = await res.json();
    setTraces(json.data ?? []);
  }, []);

  const act = useCallback(
    async (a: Agent, action: "wake" | "sleep" | "execute") => {
      setBusy(a.id);
      await fetch(`/api/agents/${a.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      await load();
      if (selected?.id === a.id) {
        const fresh = await fetch(`/api/agents/${a.id}`, { cache: "no-store" }).then((r) => r.json());
        setSelected(fresh.data);
        const t = await fetch(`/api/observability/traces?agentId=${a.id}&limit=12`, { cache: "no-store" }).then((r) => r.json());
        setTraces(t.data ?? []);
      }
      setBusy(null);
    },
    [load, selected],
  );

  const remove = useCallback(
    async (a: Agent) => {
      if (!confirm(`Remove agent '${a.name}'?`)) return;
      await fetch(`/api/agents/${a.id}`, { method: "DELETE" });
      if (selected?.id === a.id) setSelected(null);
      await load();
    },
    [load, selected],
  );

  const create = useCallback(async () => {
    if (!draft.name.trim()) return;
    setCreating(true);
    await fetch("/api/agents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(draft),
    });
    setDraft({ name: "", kind: "discord", model: "gpt-4o-mini", provider: "openai", description: "" });
    setCreating(false);
    await load();
  }, [draft, load]);

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Agent Registry"
        subtitle="Wake, execute and sleep agents in the supervisor crew"
        icon="⬡"
        action={<Pill tone="violet">{agents.length} registered</Pill>}
      />

      <Card>
        <p className="mb-3 text-xs uppercase tracking-wider text-[var(--kage-muted)]">Register new agent</p>
        <div className="grid gap-2 sm:grid-cols-5">
          <input className="k-input" placeholder="name" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
          <select className="k-input" value={draft.kind} onChange={(e) => setDraft({ ...draft, kind: e.target.value })}>
            {KINDS.map((k) => (
              <option key={k} value={k}>{k}</option>
            ))}
          </select>
          <input className="k-input" placeholder="provider" value={draft.provider} onChange={(e) => setDraft({ ...draft, provider: e.target.value })} />
          <input className="k-input" placeholder="model" value={draft.model} onChange={(e) => setDraft({ ...draft, model: e.target.value })} />
          <button className="k-btn k-btn-primary justify-center" disabled={creating} onClick={create}>
            {creating ? "…" : "+ Register"}
          </button>
        </div>
        <input className="k-input mt-2" placeholder="description (optional)" value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} />
      </Card>

      <div className="grid gap-5 lg:grid-cols-5">
        <div className="space-y-2.5 lg:col-span-3">
          {loading && <EmptyState title="Loading registry…" />}
          {!loading && agents.length === 0 && <EmptyState icon="⬡" title="No agents" hint="Register one above." />}
          {agents.map((a) => (
            <button
              key={a.id}
              onClick={() => select(a)}
              className={`k-inset k-card-hover w-full px-4 py-3 text-left ${selected?.id === a.id ? "border-violet-500/50" : ""}`}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="truncate text-sm font-semibold text-white">{a.name}</p>
                    <Pill>{a.role}</Pill>
                  </div>
                  <p className="mono mt-0.5 truncate text-[11px] text-[var(--kage-muted)]">{a.kind} · {a.provider}/{a.model}</p>
                </div>
                <div onClick={(e) => e.stopPropagation()}>
                  <StatusBadge status={a.status} live={a.status === "executing"} />
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5" onClick={(e) => e.stopPropagation()}>
                <button className="k-btn" disabled={busy === a.id} onClick={() => act(a, "wake")}>Wake</button>
                <button className="k-btn" disabled={busy === a.id} onClick={() => act(a, "execute")}>Execute</button>
                <button className="k-btn" disabled={busy === a.id} onClick={() => act(a, "sleep")}>Sleep</button>
                <button className="k-btn ml-auto text-[var(--kage-rose)]" disabled={busy === a.id} onClick={() => remove(a)}>Remove</button>
              </div>
            </button>
          ))}
        </div>

        <div className="lg:col-span-2">
          {selected ? (
            <Card>
              <SectionHeader title={selected.name} subtitle={selected.description ?? "—"} icon="⬡" action={<StatusBadge status={selected.status} live={selected.status === "executing"} />} />
              <dl className="mono mt-4 space-y-1.5 text-xs">
                <div className="flex justify-between"><dt className="text-[var(--kage-muted)]">kind</dt><dd>{selected.kind}</dd></div>
                <div className="flex justify-between"><dt className="text-[var(--kage-muted)]">role</dt><dd>{selected.role}</dd></div>
                <div className="flex justify-between"><dt className="text-[var(--kage-muted)]">model</dt><dd>{selected.provider}/{selected.model}</dd></div>
                <div className="flex justify-between"><dt className="text-[var(--kage-muted)]">last active</dt><dd>{relativeTime(selected.lastActiveAt)}</dd></div>
                <div className="flex justify-between"><dt className="text-[var(--kage-muted)]">id</dt><dd className="truncate text-[var(--kage-muted)]">{selected.id.slice(0, 8)}</dd></div>
              </dl>
              <p className="mt-5 mb-2 text-xs uppercase tracking-wider text-[var(--kage-muted)]">Decision trace</p>
              <div className="space-y-2">
                {traces.length === 0 && <p className="text-xs text-[var(--kage-muted)]">No traces yet. Execute the agent to record a decision.</p>}
                {traces.map((t) => (
                  <div key={t.id} className="k-inset px-3 py-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-[var(--kage-violet-soft)]">{t.action}</span>
                      <span className="mono text-[var(--kage-muted)]">{t.durationMs ?? 0}ms · {relativeTime(t.createdAt)}</span>
                    </div>
                    {t.decision && <p className="mt-1 text-[var(--kage-muted)]">{t.decision}</p>}
                  </div>
                ))}
              </div>
            </Card>
          ) : (
            <EmptyState icon="⬡" title="Select an agent" hint="Decision traces and config appear here." />
          )}
        </div>
      </div>
    </div>
  );
}
