// Lookup tables over a workspace, shared by the layout functions.
import type { Domain, Group, Kind, Marker, Milestone, Project, RefType, State, Workspace } from '../api/client';

export interface Index {
  ws: Workspace;
  domains: Map<string, Domain>;
  groups: Map<string, Group>;
  projects: Map<string, Project>;
  milestones: Map<string, Milestone>;
  kinds: Map<string, Kind>;
  states: Map<string, State>;
  reftypes: Map<string, RefType>;
  markers: Map<string, Marker>;
}

function byId<T extends { id: string }>(items: T[]): Map<string, T> {
  return new Map(items.map((e) => [e.id, e]));
}

export function indexWorkspace(ws: Workspace): Index {
  return {
    ws,
    domains: byId(ws.domains ?? []),
    groups: byId(ws.groups),
    projects: byId(ws.projects),
    milestones: byId(ws.milestones),
    kinds: byId(ws.kinds),
    states: byId(ws.states),
    reftypes: byId(ws.reftypes),
    markers: byId(ws.markers ?? []),
  };
}

/** Milestones of a project in project order (time, then creation). */
export function projectMilestones(idx: Index, pid: string): Milestone[] {
  const ids = idx.ws.derived.projects[pid]?.milestones ?? [];
  return ids.map((id) => idx.milestones.get(id)!).filter(Boolean);
}

/** The timeline's unit: whole days, or the time of day too. */
export type Unit = 'day' | 'hour';

/** Where a timestamp (YYYY-MM-DDTHH:MM) sits at a unit: its day, or itself. */
export const keyAt = (at: string, unit: Unit): string => (unit === 'day' ? at.slice(0, 10) : at);

/** Milliseconds of a YYYY-MM-DD date or YYYY-MM-DDTHH:MM timestamp (local time, computed as UTC). */
export function timeMs(s: string): number {
  const [date, time = '00:00'] = s.split('T');
  const [y, m, d] = date.split('-').map(Number);
  const [h, min] = time.split(':').map(Number);
  return Date.UTC(y, m - 1, d, h, min);
}

const pad = (n: number) => String(n).padStart(2, '0');

/** Today's local date as YYYY-MM-DD. */
export function localToday(now = new Date()): string {
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** The current local time as YYYY-MM-DDTHH:MM (the format of milestone timestamps). */
export function localNow(now = new Date()): string {
  return `${localToday(now)}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
}

/** A timestamp for people: "2026-11-09 14:30", or just the date at midnight. */
export const when = (at: string | null | undefined): string =>
  !at ? '' : at.endsWith('T00:00') ? at.slice(0, 10) : at.replace('T', ' ');
