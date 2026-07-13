import { useCallback, useEffect, useState } from "react";
import { getBundle, getRoutes, type Bundle, type RouteSummary } from "./api";
import { Card, LevelBadge, ProvLine, Section } from "./ui";

const params = new URLSearchParams(window.location.search);

export default function App() {
  const [routes, setRoutes] = useState<RouteSummary[]>([]);
  const [routeId, setRouteId] = useState(params.get("route") || "bom-doh-atl-qr");
  const [date, setDate] = useState(params.get("date") || "2026-08-16");
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getRoutes()
      .then(setRoutes)
      .catch((e) => setError(String(e)));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const b = await getBundle(routeId, date || undefined);
      setBundle(b);
      const u = new URL(window.location.href);
      u.searchParams.set("route", routeId);
      if (date) u.searchParams.set("date", date);
      window.history.replaceState({}, "", u.toString());
    } catch (e) {
      setError(String(e));
      setBundle(null);
    } finally {
      setLoading(false);
    }
  }, [routeId, date]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <header className="mb-6">
        <div className="flex items-center gap-3">
          <img src="/dog-plane.png" alt="fly-safe" className="h-16 w-auto" />
          <h1 className="text-2xl font-bold tracking-tight">fly-safe</h1>
        </div>
        <p className="mt-1 text-sm text-neutral-600">
          Sourced, timestamped facts for an India → US journey via a Gulf hub. No opinions — you
          decide.
        </p>
      </header>

      <Card className="mb-6">
        <div className="flex flex-wrap items-end gap-4">
          <label className="text-sm">
            <span className="mb-1 block text-xs font-medium text-neutral-500">Route</span>
            <select
              value={routeId}
              onChange={(e) => setRouteId(e.target.value)}
              className="rounded-md border border-neutral-300 bg-white px-3 py-1.5 text-sm"
            >
              {routes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-xs font-medium text-neutral-500">Travel date</span>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="rounded-md border border-neutral-300 bg-white px-3 py-1.5 text-sm"
            />
          </label>
        </div>
      </Card>

      <p className="mb-6 text-xs text-neutral-500">
        <span className="mr-3 inline-block whitespace-nowrap">
          <span className="mr-1 inline-block h-2 w-2 rounded-full bg-emerald-500 align-middle" />
          fresh
        </span>
        <span className="mr-3 inline-block whitespace-nowrap">
          <span className="mr-1 inline-block h-2 w-2 rounded-full bg-amber-500 align-middle" />
          stale
        </span>
        <span className="mr-3 inline-block whitespace-nowrap">
          <span className="mr-1 inline-block h-2 w-2 rounded-full bg-neutral-400 align-middle" />
          unavailable
        </span>
        <span className="text-neutral-400">
          — each dot shows when that fact was last confirmed with its source.
        </span>
      </p>

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          {error}. Is the API running on :8000?
        </div>
      )}
      {loading && !bundle && <p className="text-sm text-neutral-500">Loading…</p>}

      {bundle && (
        <>
          <Section
            title="Flights operating"
            subtitle="Most recent tracked operation of each leg. Live status appears closer to the travel date."
          >
            <div className="grid gap-3">
              {bundle.flights.map((f) => (
                <Card key={f.flight_number}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <span className="font-medium">{f.leg}</span>{" "}
                      <span className="text-neutral-500">· {f.flight_number}</span>
                    </div>
                    {f.available && f.status_label && (
                      <span
                        className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                          f.is_disrupted
                            ? "bg-red-100 text-red-800"
                            : "bg-emerald-100 text-emerald-800"
                        }`}
                      >
                        {f.status_label}
                      </span>
                    )}
                  </div>
                  {f.available ? (
                    <div className="mt-1 text-sm text-neutral-600">
                      {f.latest_date} · dep {f.dep_scheduled_local?.slice(11, 16)}
                      {typeof f.delay_minutes === "number" && f.delay_minutes > 0 && (
                        <span className="text-amber-700"> (+{f.delay_minutes}m)</span>
                      )}
                      {f.aircraft && <span className="text-neutral-400"> · {f.aircraft}</span>}
                    </div>
                  ) : (
                    <div className="mt-1 text-sm text-neutral-500">{f.note}</div>
                  )}
                  <ProvLine prov={f.provenance} />
                </Card>
              ))}
            </div>
          </Section>

          <Section
            title="Government travel advisories"
            subtitle="Official levels for the countries on your itinerary, reported verbatim."
          >
            <div className="grid gap-3">
              {bundle.advisories.map((a) => (
                <Card key={a.country_code}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium">{a.country_name}</span>
                    {a.available && typeof a.level === "number" ? (
                      <LevelBadge level={a.level} label={a.label || ""} />
                    ) : (
                      <span className="text-right text-xs text-neutral-500">{a.note}</span>
                    )}
                  </div>
                  {a.available && a.link && (
                    <a
                      href={a.link}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 inline-block text-xs text-neutral-500 underline decoration-dotted"
                    >
                      Read the advisory →
                    </a>
                  )}
                  <ProvLine prov={a.provenance} />
                </Card>
              ))}
            </div>
          </Section>

          <Section title="Airspace bulletins" subtitle={bundle.airspace_note}>
            <div className="grid gap-3">
              {bundle.airspace.length === 0 && (
                <Card>
                  <p className="text-sm text-neutral-500">
                    No active conflict-zone bulletins matched for this corridor.
                  </p>
                </Card>
              )}
              {bundle.airspace.map((c) => (
                <Card key={c.identifier}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium">{c.title}</span>
                    <span className="shrink-0 rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-800">
                      {c.status}
                    </span>
                  </div>
                  <div className="mt-1 text-sm text-neutral-600">
                    {c.identifier}
                    {c.valid_until && ` · valid until ${c.valid_until}`}
                  </div>
                  {c.url && (
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 inline-block text-xs text-neutral-500 underline decoration-dotted"
                    >
                      View bulletin →
                    </a>
                  )}
                  <ProvLine prov={c.provenance} />
                </Card>
              ))}
            </div>
          </Section>

          <Section title={`How ${bundle.airline_name} handled past escalations`}>
            <div className="grid gap-3">
              {bundle.history.map((h, i) => (
                <Card key={i}>
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="font-medium">{h.title}</span>
                    <span className="shrink-0 text-xs text-neutral-500">{h.date}</span>
                  </div>
                  <p className="mt-1 text-sm text-neutral-600">{h.summary}</p>
                  <p className="mt-2 text-sm">
                    <span className="font-medium">Response: </span>
                    {h.airline_response}
                  </p>
                  <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-neutral-500">
                    {h.sources.map((s, j) => (
                      <a
                        key={j}
                        href={s.url}
                        target="_blank"
                        rel="noreferrer"
                        className="underline decoration-dotted"
                      >
                        {s.label}
                      </a>
                    ))}
                  </p>
                </Card>
              ))}
            </div>
          </Section>

          <footer className="mt-8 border-t border-neutral-200 pt-4 text-xs text-neutral-500">
            <p>{bundle.disclaimer}</p>
            <p className="mt-1">Generated {new Date(bundle.generated_at).toLocaleString()}.</p>
          </footer>
        </>
      )}
    </div>
  );
}
