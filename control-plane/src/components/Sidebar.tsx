"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Overview", icon: "◈" },
  { href: "/agents", label: "Agents", icon: "⬡" },
  { href: "/workflows", label: "Workflows", icon: "⇄" },
  { href: "/integrations", label: "Integrations", icon: "⊞" },
  { href: "/observability", label: "Observability", icon: "◉" },
  { href: "/config", label: "Configuration", icon: "⚙" },
  { href: "/docs", label: "Documentation", icon: "❒" },
];

export default function Sidebar({ version, codename }: { version: string; codename: string }) {
  const pathname = usePathname();
  return (
    <aside className="k-grid flex h-screen w-60 flex-col border-r border-[var(--kage-border)] bg-[var(--kage-bg-2)]/80 backdrop-blur-xl">
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-600 shadow-lg shadow-violet-900/40">
          <span className="text-lg font-bold text-white">影</span>
        </div>
        <div>
          <p className="text-sm font-semibold leading-tight text-white">KAGE OS</p>
          <p className="mono text-[10px] uppercase tracking-widest text-[var(--kage-muted)]">supervisor</p>
        </div>
      </div>

      <nav className="mt-2 flex-1 space-y-1 px-3">
        {NAV.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-violet-500/15 text-white"
                  : "text-[var(--kage-muted)] hover:bg-white/5 hover:text-white"
              }`}
            >
              <span
                className={`mono text-base ${active ? "text-[var(--kage-violet-soft)]" : "text-[var(--kage-muted)] group-hover:text-white"}`}
              >
                {item.icon}
              </span>
              {item.label}
              {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-[var(--kage-violet-soft)]" />}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-[var(--kage-border)] px-5 py-4">
        <div className="flex items-center gap-2">
          <span className="k-live h-2 w-2 rounded-full bg-[var(--kage-emerald)]" />
          <span className="text-xs text-[var(--kage-muted)]">supervisor nominal</span>
        </div>
        <p className="mono mt-2 text-[10px] text-[var(--kage-muted)]">
          v{version} · {codename}
        </p>
      </div>
    </aside>
  );
}
