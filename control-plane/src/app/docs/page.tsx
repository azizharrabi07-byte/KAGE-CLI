"use client";

import { useState } from "react";
import { Card, SectionHeader, Pill } from "@/components/ui";

const TABS = ["architecture", "developer", "api", "examples", "troubleshooting", "changelog"] as const;
type Tab = (typeof TABS)[number];

function Code({ children }: { children: string }) {
  return <pre className="mono mt-2 overflow-auto rounded-lg bg-black/50 p-3 text-[11px] leading-relaxed text-[#cdd6f4]">{children}</pre>;
}
function H({ children }: { children: string }) {
  return <h3 className="mt-5 text-sm font-semibold text-white">{children}</h3>;
}
function P({ children }: { children: React.ReactNode }) {
  return <p className="mt-2 text-sm leading-relaxed text-[var(--kage-muted)]">{children}</p>;
}

export default function DocsPage() {
  const [tab, setTab] = useState<Tab>("architecture");
  return (
    <div className="space-y-6">
      <SectionHeader title="Documentation" subtitle="Architecture, developer guide, API reference, examples and troubleshooting" icon="❒" action={<Pill tone="violet">v3.0.0</Pill>} />

      <div className="flex flex-wrap gap-1.5">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)} className={`k-btn capitalize ${tab === t ? "k-btn-primary" : ""}`}>{t}</button>
        ))}
      </div>

      <Card>
        {tab === "architecture" && (
          <div>
            <H>System layers</H>
            <P>KAGE OS is structured as a supervisor controlling a crew of agents through a typed tool layer, with a persisted workflow engine on top and a control plane (this UI) for humans.</P>
            <Code>{`┌─ Control Plane (Next.js + Postgres) ──────────────┐
│  Overview · Agents · Workflows · Integrations      │
│  Observability · Configuration · Docs              │
└───────────────────────┬───────────────────────────┘
                        │  HTTP (JSON ToolResult envelopes)
┌─ Supervisor Core ─────▼───────────────────────────┐
│  Registry (wake/execute/sleep) · Workflow Engine   │
│  Health (retry/timeout/auto-reconnect) · Cache     │
└───────┬──────────────────┬──────────────────┬──────┘
        │ agents           │ tools            │ integrations
   discord telegram      browser shell      discord telegram
   whatsapp obsidian     memory crew        whatsapp obsidian
   system  meta          ...                llm-provider postgres`}</Code>
            <H>Data flow</H>
            <P>1) A trigger (manual run, slash command, scheduled tick) calls the supervisor. 2) The workflow engine resolves the current step from persisted state, executes the owning agent's tool with retry/timeout, and evaluates the optional branch rule. 3) Each step emits a structured log, metrics and a trace span. 4) State is written back so runs resume after restart.</P>
          </div>
        )}

        {tab === "developer" && (
          <div>
            <H>Register a new agent</H>
            <P>Agents are rows in the <span className="mono text-white">agents</span> table with a <span className="mono text-white">kind</span>. Add a row via the UI or POST <span className="mono text-white">/api/agents</span>.</P>
            <Code>{`POST /api/agents
{ "name": "Slack-Bridge", "kind": "telegram",
  "provider": "openai", "model": "gpt-4o-mini" }`}</Code>
            <H>Add a tool / action</H>
            <P>Actions are simulated in <span className="mono text-white">src/lib/workflow-engine.ts → actionData()</span>. Add a case returning a structured payload; the engine handles retry, timeout, branching and observability automatically.</P>
            <H>Return contract</H>
            <P>Every tool returns a consistent envelope so branching and the UI stay uniform:</P>
            <Code>{`{ "status": "ok" | "error",
  "data": <any> | null,
  "error": string | null,
  "durationMs": number, "attempts": number }`}</Code>
          </div>
        )}

        {tab === "api" && (
          <div>
            <H>REST surface</H>
            <Code>{`GET    /api/health                 liveness + version
GET    /api/system                 dashboard overview
GET    /api/agents                 list registry
POST   /api/agents                 register agent
GET    /api/agents/:id             detail
PATCH  /api/agents/:id             wake | sleep | execute
DELETE /api/agents/:id             remove
GET    /api/workflows              list
POST   /api/workflows              create (definition)
GET    /api/workflows/:id          status + state
PATCH  /api/workflows/:id          pause | cancel | reset
POST   /api/workflows/:id/run      { mode: 'step' | 'complete' }
GET    /api/integrations           list health
POST   /api/integrations           refresh all
POST   /api/integrations/:id/check single probe
PATCH  /api/integrations/:id       enable | autoReconnect | config
GET    /api/observability/logs     ?level=&source=&limit=
GET    /api/observability/metrics  summary + series
GET    /api/observability/traces   ?agentId=&limit=
GET    /api/secrets   POST   DELETE(?key=)
GET    /api/config    PUT
POST   /api/tools/shell            { command, dryRun }`}</Code>
          </div>
        )}

        {tab === "examples" && (
          <div>
            <H>Conditional branching + retry</H>
            <Code>{`{
  "name": "Discord Onboarding",
  "definition": {
    "entryStepId": "recall",
    "steps": [
      { "id": "recall", "name": "Recall context",
        "agent": "memory", "action": "memory.recall" },
      { "id": "decide", "name": "Compose greeting",
        "agent": "discord", "action": "llm.complete",
        "retry": { "maxAttempts": 3, "baseDelayMs": 100 },
        "branch": { "field": "status", "equals": "ok",
                    "thenStepId": "send", "elseStepId": "fallback" } },
      { "id": "send", "agent": "discord", "action": "discord.send", "next": null },
      { "id": "fallback", "agent": "obsidian", "action": "obsidian.write", "next": null }
    ]
  }
}`}</Code>
            <H>Sandboxed shell (dry-run)</H>
            <Code>{`curl -X POST $URL/api/tools/shell \\
  -H 'content-type: application/json' \\
  -d '{"command":"ls -la","dryRun":true}'`}</Code>
          </div>
        )}

        {tab === "troubleshooting" && (
          <div>
            <H>Integration shows "down"</H>
            <P>Most probes fail because the required credential is missing. Open Configuration → Secrets, add the token (e.g. <span className="mono text-white">DISCORD_TOKEN</span>), then re-check the integration. The probe verifies presence + measures latency.</P>
            <H>Workflow stuck on "running"</H>
            <P>Use <span className="mono text-white">Step →</span> to advance one step, or <span className="mono text-white">Reset</span> to clear persisted state and start over. State is stored in <span className="mono text-white">workflows.state</span> so runs survive restarts.</P>
            <H>Shell command rejected</H>
            <P>The sandbox allow-lists read-only commands and forbids absolute paths, subshells and network tools. Try <span className="mono text-white">ls</span>, <span className="mono text-white">cat</span>, <span className="mono text-white">grep</span> within <span className="mono text-white">/tmp/kage-sandbox</span>.</P>
            <H>Cache not deduplicating</H>
            <P>Check Configuration → Cache; TTL and disk toggle are read from <span className="mono text-white">KAGE_CACHE_TTL_MS</span> / <span className="mono text-white">KAGE_CACHE_DISK</span>.</P>
          </div>
        )}

        {tab === "changelog" && (
          <div>
            <H>3.0.0 — supervisor-discord</H>
            <P>Phases 3–8 delivered as the KAGE OS control plane: configuration wizard, integration health (retry/timeout/auto-reconnect), workflow engine with branching + per-step backoff + resumable persistence, two-tier cache, secret vault, sandboxed shell, structured logs/metrics/traces, documentation hub and CI/release automation.</P>
            <H>2.0.0</H>
            <P>Supervisor daemon with IPC, multi-agent registry, Discord slash commands, tool framework (browser/shell/memory/crew) and the initial workflow engine.</P>
            <H>1.0.0</H>
            <P>Initial KAGE CLI scaffold.</P>
          </div>
        )}
      </Card>
    </div>
  );
}
