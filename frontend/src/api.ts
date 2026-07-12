const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export type Freshness = "fresh" | "stale" | "unavailable";

export interface Provenance {
  source: string;
  source_url: string;
  tier: string;
  fetched_at: string;
  freshness: Freshness;
}

export interface Flight {
  leg: string;
  flight_number: string;
  available: boolean;
  latest_date?: string | null;
  status?: string | null;
  status_label?: string | null;
  is_disrupted: boolean;
  dep_scheduled_local?: string | null;
  dep_revised_local?: string | null;
  arr_scheduled_local?: string | null;
  delay_minutes?: number | null;
  aircraft?: string | null;
  note?: string | null;
  provenance?: Provenance | null;
}

export interface Advisory {
  country_code: string;
  country_name: string;
  available: boolean;
  level?: number | null;
  label?: string | null;
  link?: string | null;
  published?: string | null;
  note?: string | null;
  provenance?: Provenance | null;
}

export interface Airspace {
  identifier: string;
  title: string;
  status: string;
  valid_until?: string | null;
  url?: string | null;
  provenance?: Provenance | null;
}

export interface HistorySource {
  label: string;
  url: string;
}

export interface HistoryCard {
  airline: string;
  date: string;
  title: string;
  summary: string;
  airline_response: string;
  sources: HistorySource[];
}

export interface RouteSummary {
  id: string;
  label: string;
  origin: string;
  hub: string;
  destination: string;
  airline: string;
  airline_name: string;
}

export interface Bundle {
  route_id: string;
  label: string;
  airline: string;
  airline_name: string;
  origin: string;
  hub: string;
  destination: string;
  travel_date?: string | null;
  flights: Flight[];
  advisories: Advisory[];
  airspace: Airspace[];
  airspace_note: string;
  history: HistoryCard[];
  disclaimer: string;
  generated_at: string;
}

export async function getRoutes(): Promise<RouteSummary[]> {
  const r = await fetch(`${API}/routes`);
  if (!r.ok) throw new Error(`Could not load routes (${r.status})`);
  return r.json();
}

export async function getBundle(id: string, date?: string): Promise<Bundle> {
  const u = new URL(`${API}/route/${id}`);
  if (date) u.searchParams.set("date", date);
  const r = await fetch(u.toString());
  if (!r.ok) throw new Error(`Could not load route data (${r.status})`);
  return r.json();
}
