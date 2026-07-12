import type { ReactNode } from "react";
import type { Provenance } from "./api";

export function timeAgo(iso: string): string {
  const secs = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (secs < 90) return "just now";
  const mins = secs / 60;
  if (mins < 90) return `${Math.round(mins)} min ago`;
  const hrs = mins / 60;
  if (hrs < 36) return `${Math.round(hrs)} h ago`;
  return `${Math.round(hrs / 24)} d ago`;
}

const FRESH_DOT: Record<string, string> = {
  fresh: "bg-emerald-500",
  stale: "bg-amber-500",
  unavailable: "bg-neutral-400",
};

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-neutral-200 bg-white p-4 ${className}`}>{children}</div>
  );
}

export function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section className="mb-7">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">{title}</h2>
      {subtitle && <p className="mb-2 mt-0.5 text-xs text-neutral-500">{subtitle}</p>}
      <div className="mt-2">{children}</div>
    </section>
  );
}

export function ProvLine({ prov }: { prov?: Provenance | null }) {
  if (!prov) {
    return <p className="mt-2 text-xs text-neutral-400">No data — check the official source.</p>;
  }
  const verb =
    prov.freshness === "fresh"
      ? "confirmed"
      : prov.freshness === "stale"
        ? "last confirmed"
        : "unavailable";
  return (
    <p className="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-neutral-500">
      <span className={`inline-block h-2 w-2 rounded-full ${FRESH_DOT[prov.freshness]}`} />
      <span>
        {verb} {timeAgo(prov.fetched_at)}
      </span>
      <span className="text-neutral-300">·</span>
      <a
        href={prov.source_url}
        target="_blank"
        rel="noreferrer"
        className="underline decoration-dotted hover:text-neutral-800"
      >
        source: {prov.source}
      </a>
    </p>
  );
}

const LEVEL_STYLE: Record<number, string> = {
  1: "bg-emerald-100 text-emerald-800",
  2: "bg-yellow-100 text-yellow-800",
  3: "bg-orange-100 text-orange-800",
  4: "bg-red-100 text-red-800",
};

export function LevelBadge({ level, label }: { level: number; label: string }) {
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${LEVEL_STYLE[level] ?? "bg-neutral-100 text-neutral-700"}`}
    >
      Level {level}: {label}
    </span>
  );
}
