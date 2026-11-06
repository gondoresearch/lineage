// Project filters shared by the timeline, status board and dependencies view.
import type { Workspace } from '../api/client';

export interface Filters {
  /** group ids to show; empty = all */
  groups: string[];
  /** current-state ids to show; empty = all */
  states: string[];
  hideInactive: boolean;
}

export const NO_FILTERS: Filters = { groups: [], states: [], hideInactive: false };

/** Inactive: the current state waits on nobody, or there is no head yet (all milestones planned). */
export function isInactive(ws: Workspace, pid: string): boolean {
  const state = ws.derived.projects[pid]?.current_state;
  if (!state) return true;
  return ws.states.find((s) => s.id === state)?.waiting_on === 'nobody';
}

export function projectFilter(ws: Workspace, f: Filters): (pid: string) => boolean {
  const group = new Map(ws.projects.map((p) => [p.id, p.group]));
  return (pid) => {
    if (f.groups.length && !f.groups.includes(group.get(pid) ?? '')) return false;
    const state = ws.derived.projects[pid]?.current_state ?? '';
    if (f.states.length && !f.states.includes(state)) return false;
    if (f.hideInactive && isInactive(ws, pid)) return false;
    return true;
  };
}

export function isFiltered(f: Filters): boolean {
  return f.groups.length > 0 || f.states.length > 0 || f.hideInactive;
}
