import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import { VERSION, CODENAME } from "@/lib/version";

export const metadata: Metadata = {
  title: "KAGE OS — Supervisor Control Plane",
  description:
    "Production control plane for the KAGE OS multi-agent supervisor: agents, workflows, integrations, observability and configuration.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">
        <div className="flex min-h-screen">
          <Sidebar version={VERSION} codename={CODENAME} />
          <main className="flex-1 overflow-x-hidden">
            <div className="mx-auto w-full max-w-6xl px-6 py-8 lg:px-10">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
