// KAGE OS — single source of truth for semantic versioning (Phase 8).
// Keep this in sync with CHANGELOG.md.
export const VERSION = "3.0.0";
export const CODENAME = "supervisor-discord";

export const VERSION_INFO = {
  version: VERSION,
  codename: CODENAME,
  // Lifecycle status of each delivered phase.
  phases: {
    "1": "Supervisor daemon + IPC",
    "2": "Multi-agent registry + Discord UI + tool framework",
    "3": "Production configuration (wizard + settings)",
    "4": "Integration health, retry/timeout, auto-reconnect",
    "5": "Workflow engine (branching, retries, persistence)",
    "6": "Caching, secrets, validation, sandbox, logs, metrics, traces",
    "7": "Tests + documentation hub",
    "8": "CI/release, versioning, changelog",
  },
} as const;
