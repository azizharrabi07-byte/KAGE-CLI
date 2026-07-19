"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, SectionHeader, Pill, EmptyState } from "@/components/ui";

type Secret = { id: string; key: string; scope: string; maskedValue: string; hint: string | null; enabled: boolean; createdAt: string };
type CacheStats = { memoryKeys: number; memoryHits: number; diskHits: number; diskWrites: number; ttlMs: number; diskEnabled: boolean };

const TABS = ["settings", "secrets", "cache"] as const;
type Tab = (typeof TABS)[number];

const BOOL_FIELDS: Array<{ key: string; label: string }> = [
  { key: "sandboxEnabled", label: "Sandbox shell execution" },
  { key: "autoReconnect", label: "Auto-reconnect integrations" },
];

export default function ConfigPage() {
  const [tab, setTab] = useState<Tab>("settings");
  const [cfg, setCfg] = useState<Record<string, unknown>>({});
  const [saved, setSaved] = useState(false);
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [cache, setCache] = useState<CacheStats | null>(null);
  const [newSecret, setNewSecret] = useState({ key: "", value: "", scope: "global" });

  const loadCfg = useCallback(async () => {
    const r = await fetch("/api/config", { cache: "no-store" });
    setCfg((await r.json()).data ?? {});
  }, []);
  const loadSecrets = useCallback(async () => {
    const r = await fetch("/api/secrets", { cache: "no-store" });
    setSecrets((await r.json()).data ?? []);
  }, []);
  const loadCache = useCallback(async () => {
    const r = await fetch("/api/cache", { cache: "no-store" });
    setCache((await r.json()).data ?? null);
  }, []);

  useEffect(() => {
    loadCfg();
    loadSecrets();
    loadCache();
  }, [loadCfg, loadSecrets, loadCache]);

  const save = useCallback(async () => {
    setSaved(false);
    await fetch("/api/config", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cfg) });
    setSaved(true);
    setTimeout(() => setSaved(false), 1800);
  }, [cfg]);

  const addSecret = useCallback(async () => {
    if (!newSecret.key || !newSecret.value) return;
    await fetch("/api/secrets", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(newSecret) });
    setNewSecret({ key: "", value: "", scope: "global" });
    await loadSecrets();
  }, [newSecret, loadSecrets]);

  const removeSecret = useCallback(async (key: string) => {
    await fetch(`/api/secrets?key=${encodeURIComponent(key)}`, { method: "DELETE" });
    await loadSecrets();
  }, [loadSecrets]);

  const clearCache = useCallback(async () => {
    await fetch("/api/cache", { method: "DELETE" });
    await loadCache();
  }, [loadCache]);

  return (
    <div className="space-y-6">
      <SectionHeader title="Configuration" subtitle="Setup wizard, secret vault and cache controls" icon="⚙" />

      <div className="flex gap-1.5">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)} className={`k-btn capitalize ${tab === t ? "k-btn-primary" : ""}`}>{t}</button>
        ))}
      </div>

      {tab === "settings" && (
        <Card>
          <SectionHeader title="Setup wizard" subtitle="Provider, model, concurrency and runtime behaviour" icon="✦" action={saved ? <Pill tone="emerald">saved</Pill> : undefined} />
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <Field label="Default provider">
              <select className="k-input" value={String(cfg.defaultProvider ?? "openai")} onChange={(e) => setCfg({ ...cfg, defaultProvider: e.target.value })}>
                {["openai", "anthropic", "google", "mistral", "local"].map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </Field>
            <Field label="Default model">
              <input className="k-input" value={String(cfg.defaultModel ?? "")} onChange={(e) => setCfg({ ...cfg, defaultModel: e.target.value })} />
            </Field>
            <Field label="Max concurrency">
              <input type="number" className="k-input" value={Number(cfg.maxConcurrency ?? 4)} onChange={(e) => setCfg({ ...cfg, maxConcurrency: Number(e.target.value) })} />
            </Field>
            <Field label="Cache TTL (ms)">
              <input type="number" className="k-input" value={Number(cfg.cacheTtlMs ?? 60000)} onChange={(e) => setCfg({ ...cfg, cacheTtlMs: Number(e.target.value) })} />
            </Field>
            <Field label="Log level">
              <select className="k-input" value={String(cfg.logLevel ?? "info")} onChange={(e) => setCfg({ ...cfg, logLevel: e.target.value })}>
                {["debug", "info", "warn", "error", "trace"].map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
            </Field>
            <Field label="Output format (batch mode)">
              <select className="k-input" value={String(cfg.outputFormat ?? "text")} onChange={(e) => setCfg({ ...cfg, outputFormat: e.target.value })}>
                {["text", "json", "yaml"].map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </Field>
          </div>
          <div className="mt-4 space-y-2">
            {BOOL_FIELDS.map((f) => (
              <label key={f.key} className="k-inset flex cursor-pointer items-center justify-between px-3.5 py-2.5">
                <span className="text-sm text-white">{f.label}</span>
                <input type="checkbox" checked={Boolean(cfg[f.key] ?? true)} onChange={(e) => setCfg({ ...cfg, [f.key]: e.target.checked })} className="h-4 w-4 accent-violet-500" />
              </label>
            ))}
          </div>
          <button className="k-btn k-btn-primary mt-4" onClick={save}>Save configuration</button>
        </Card>
      )}

      {tab === "secrets" && (
        <Card>
          <SectionHeader title="Secret vault" subtitle="Masked references only — plaintext resolves from the environment at runtime" icon="⚿" />
          <div className="mt-4 grid gap-2 sm:grid-cols-4">
            <input className="k-input sm:col-span-1" placeholder="KEY (e.g. DISCORD_TOKEN)" value={newSecret.key} onChange={(e) => setNewSecret({ ...newSecret, key: e.target.value.toUpperCase() })} />
            <input className="k-input sm:col-span-2" placeholder="value (stored masked)" value={newSecret.value} onChange={(e) => setNewSecret({ ...newSecret, value: e.target.value })} />
            <button className="k-btn k-btn-primary justify-center" onClick={addSecret}>Add secret</button>
          </div>
          <div className="mt-4 space-y-2">
            {secrets.length === 0 && <EmptyState icon="⚿" title="No secrets" hint="Add a token — it is stored masked only." />}
            {secrets.map((s) => (
              <div key={s.id} className="k-inset flex items-center justify-between px-3.5 py-2.5">
                <div>
                  <p className="mono text-sm text-white">{s.key}</p>
                  <p className="mono text-[11px] text-[var(--kage-muted)]">{s.maskedValue} · {s.scope}</p>
                </div>
                <button className="k-btn text-[var(--kage-rose)]" onClick={() => removeSecret(s.key)}>Remove</button>
              </div>
            ))}
          </div>
        </Card>
      )}

      {tab === "cache" && cache && (
        <Card>
          <SectionHeader title="Response cache" subtitle="Two-tier in-memory + disk cache for LLM responses" icon="⋓" action={<button className="k-btn" onClick={clearCache}>Clear cache</button>} />
          <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-3">
            <Stat label="Memory keys" value={cache.memoryKeys} />
            <Stat label="Memory hits" value={cache.memoryHits} />
            <Stat label="Disk enabled" value={cache.diskEnabled ? "yes" : "no"} />
            <Stat label="Disk hits" value={cache.diskHits} />
            <Stat label="Disk writes" value={cache.diskWrites} />
            <Stat label="TTL" value={`${(cache.ttlMs / 1000).toFixed(0)}s`} />
          </div>
        </Card>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] uppercase tracking-wider text-[var(--kage-muted)]">{label}</span>
      {children}
    </label>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="k-inset p-4">
      <p className="text-[11px] uppercase tracking-wider text-[var(--kage-muted)]">{label}</p>
      <p className="mono mt-1 text-xl font-semibold text-white">{value}</p>
    </div>
  );
}
