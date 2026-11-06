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

/** Milestones of a project in project order (date, then creation). */
export function projectMilestones(idx: Index, pid: string): Milestone[] {
  const ids = idx.ws.derived.projects[pid]?.milestones ?? [];
  return ids.map((id) => idx.milestones.get(id)!).filter(Boolean);
}

/** Milliseconds (UTC) of a YYYY-MM-DD date. */
export function dayMs(date: string): number {
  const [y, m, d] = date.split('-').map(Number);
  return Date.UTC(y, m - 1, d);
}

/** Today's local date as YYYY-MM-DD. */
export function localToday(now = new Date()): string {
  const p = (n: number) => String(n).padStart(2, '0');
  return `${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())}`;
}
