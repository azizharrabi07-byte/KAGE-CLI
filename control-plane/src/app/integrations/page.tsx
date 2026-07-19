"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, SectionHeader, StatusBadge, Pill, EmptyState } from "@/components/ui";
import { relativeTime, formatMs } from "@/lib/format";

type Integration = {
  id: string;
  name: string;
  kind: string;
  enabled: boolean;
  status: string;
  latencyMs: number | null;
  lastCheckedAt: string | null;
  errorMessage: string | null;
  retries: number;
  autoReconnect: boolean;
  config: Record<string, unknown>;
};

export default function IntegrationsPage() {
  const [items, setItems] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    const res = await fetch("/api/integrations", { cache: "no-store" });
    const j = await res.json();
    setItems(j.data ?? []);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const checkAll = useCallback(async () => {
    setBusy("all");
    await fetch("/api/integrations", { method: "POST" });
    await load();
    setBusy(null);
  }, [load]);

  const checkOne = useCallback(
    async (id: string) => {
      setBusy(id);
      await fetch(`/api/integrations/${id}/check`, { method: "POST" });
      await load();
      setBusy(null);
    },
    [load],
  );

  const patch = useCallback(
    async (id: string, body: Record<string, unknown>) => {
      await fetch(`/api/integrations/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      await load();
    },
    [load],
  );

  const healthy = items.filter((i) => i.status === "healthy").length;

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Integration Health"
        subtitle="Retry, timeout and auto-reconnect posture for every connected service"
        icon="⊞"
        action={
          <button className="k-btn k-btn-primary" disabled={busy === "all"} onClick={checkAll}>
            {busy === "all" ? "Probing…" : "⟳ Check all"}
          </button>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div className="k-inset p-4"><p className="text-[11px] uppercase tracking-wider text-[var(--kage-muted)]">Healthy</p><p className="mono mt-1 text-2xl font-semibold text-[var(--kage-emerald)]">{healthy}</p></div>
        <div className="k-inset p-4"><p className="text-[11px] uppercase tracking-wider text-[var(--kage-muted)]">Degraded</p><p className="mono mt-1 text-2xl font-semibold text-[var(--kage-amber)]">{items.filter((i) => i.status === "degraded").length}</p></div>
        <div className="k-inset p-4"><p className="text-[11px] uppercase tracking-wider text-[var(--kage-muted)]">Down</p><p className="mono mt-1 text-2xl font-semibold text-[var(--kage-rose)]">{items.filter((i) => i.status === "down").length}</p></div>
        <div className="k-inset p-4"><p className="text-[11px] uppercase tracking-wider text-[var(--kage-muted)]">Enabled</p><p className="mono mt-1 text-2xl font-semibold text-white">{items.filter((i) => i.enabled).length}</p></div>
      </div>

      {loading && <EmptyState title="Loading integrations…" />}
      {!loading && (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((i) => (
            <Card key={i.id} hover>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-base font-semibold text-white">{i.name}</p>
                    <Pill>{i.kind}</Pill>
                  </div>
                  <p className="mono mt-1 text-[11px] text-[var(--kage-muted)]">
                    latency {formatMs(i.latencyMs)} · checked {relativeTime(i.lastCheckedAt)}
                  </p>
                </div>
                <StatusBadge status={i.enabled ? i.status : "disabled"} live={i.status === "healthy"} />
              </div>

              {i.errorMessage && i.status !== "healthy" && (
                <p className="mono mt-2 rounded-md bg-rose-500/10 px-2 py-1 text-[11px] text-[var(--kage-rose)]">⚠ {i.errorMessage}</p>
              )}

              <div className="mono mt-3 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-[var(--kage-muted)]">
                <span>retries: {i.retries}</span>
                <span>auto-reconnect: {i.autoReconnect ? "on" : "off"}</span>
                <span>config: {Object.keys(i.config).join(", ") || "—"}</span>
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-2">
                <button className="k-btn" disabled={busy === i.id} onClick={() => checkOne(i.id)}>{busy === i.id ? "…" : "Check now"}</button>
                <button className="k-btn" onClick={() => patch(i.id, { enabled: !i.enabled })}>{i.enabled ? "Disable" : "Enable"}</button>
                <button className="k-btn" onClick={() => patch(i.id, { autoReconnect: !i.autoReconnect })}>Reconnect: {i.autoReconnect ? "on" : "off"}</button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
