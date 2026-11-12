// Legend hiding and hover highlighting (no DOM): which marks belong to a legend
// entry (a group, kind, state, reference type or marker), and which are hidden.
import type { Workspace } from '../api/client';

export type Cat = 'group' | 'kind' | 'state' | 'reftype' | 'marker';
export const CATS: Cat[] = ['group', 'kind', 'state', 'reftype', 'marker'];
export interface LegendKey {
  cat: Cat;
  id: string;
}
/** Built-in rows of the Markers column (ids cannot clash with user markers). */
export const PLANNED = '@planned';
export const OVERDUE = '@overdue';
export const TODAY = '@today';
export const BUILTIN_MARKERS = [PLANNED, OVERDUE, TODAY];

export type Hidden = Record<Cat, string[]>;

export const noHidden = (): Hidden => ({ group: [], kind: [], state: [], reftype: [], marker: [] });

export function isHidden(h: Hidden, k: LegendKey): boolean {
  return h[k.cat].includes(k.id);
}

export function anyHidden(h: Hidden): boolean {
  return CATS.some((c) => h[c].length > 0);
}

/** Every id of a category in the workspace. */
export function idsOf(ws: Workspace, cat: Cat): string[] {
  switch (cat) {
    case 'group': return ws.groups.map((g) => g.id);
    case 'kind': return ws.kinds.map((k) => k.id);
    case 'state': return ws.states.map((s) => s.id);
    case 'reftype': return ws.reftypes.map((r) => r.id);
    case 'marker': return [...BUILTIN_MARKERS, ...(ws.markers ?? []).map((m) => m.id)];
  }
}

export function toggleHidden(h: Hidden, k: LegendKey): void {
  const l = h[k.cat];
  const i = l.indexOf(k.id);
  if (i >= 0) l.splice(i, 1);
  else l.push(k.id);
}

/** Hide every entry of the category except `k`. */
export function showOnly(ws: Workspace, h: Hidden, k: LegendKey): void {
  h[k.cat] = idsOf(ws, k.cat).filter((id) => id !== k.id);
}

export function showAll(h: Hidden, cat: Cat): void {
  h[cat] = [];
}

/** Does a milestone belong to the entry? (a state: the one styling its line) */
function milestoneIn(k: LegendKey, m: { id: string; kind: string; state?: string | null; planned?: boolean; markers?: string[] | null }, group: string | undefined, overdue: Set<string>): boolean {
  switch (k.cat) {
    case 'group': return group === k.id;
    case 'kind': return m.kind === k.id;
    case 'state': return m.state === k.id;
    case 'marker':
      if (k.id === PLANNED) return !!m.planned;
      if (k.id === OVERDUE) return overdue.has(m.id);
      if (k.id === TODAY) return false; // only the today line is of this entry
      return (m.markers ?? []).includes(k.id);
    case 'reftype': return false;
  }
}

/** Hover highlighting: which marks belong to the hovered legend entry. */
/** `overdue`: ids of the overdue planned milestones (they depend on today). */
export function legendMatcher(ws: Workspace, k: LegendKey | null, overdue: Set<string> = new Set()) {
  const group = new Map(ws.projects.map((p) => [p.id, p.group]));
  const ms = new Map(ws.milestones.map((m) => [m.id, m]));
  const refType = new Map(ws.references.map((r) => [r.id, r.type]));
  const milestone = (id: string | null) => {
    if (!k || id === null) return true;
    const m = ms.get(id);
    return !!m && milestoneIn(k, m, group.get(m.project), overdue);
  };
  return {
    milestone,
    /** a line (state segment) or edge between two milestones */
    segment: (from: string, to: string | null) => !k || (k.cat === 'reftype' ? false : milestone(from)),
    edge: (kind: 'fork' | 'merge' | 'reference', id: string, from: string, to: string) => {
      if (!k) return true;
      if (k.cat === 'reftype') return kind === 'reference' && refType.get(id) === k.id;
      return milestone(from) && milestone(to);
    },
    project: (pid: string) => {
      if (!k) return true;
      if (k.cat === 'group') return group.get(pid) === k.id;
      if (k.cat === 'reftype') return true;
      return (ws.derived.projects[pid]?.milestones ?? []).some(milestone);
    },
  };
}

/** What is visible under the hidden entries. Groups hide whole lanes (see `projectVisible`). */
export function visibility(ws: Workspace, h: Hidden) {
  const ms = new Map(ws.milestones.map((m) => [m.id, m]));
  const group = new Map(ws.projects.map((p) => [p.id, p.group]));
  const refType = new Map(ws.references.map((r) => [r.id, r.type]));
  const milestone = (id: string) => {
    const m = ms.get(id);
    return !m || (!h.kind.includes(m.kind) && !(m.planned && h.marker.includes(PLANNED)));
  };
  return {
    milestone,
    projectVisible: (pid: string) => !h.group.includes(group.get(pid) ?? ''),
    /** a line is hidden with its state */
    segment: (from: string, faded = false) => {
      if (faded && h.marker.includes(PLANNED)) return false;
      const st = ms.get(from)?.state;
      return !st || !h.state.includes(st);
    },
    /** references are hidden with their type; any edge with a hidden end */
    edge: (kind: 'fork' | 'merge' | 'reference', id: string) => kind !== 'reference' || !h.reftype.includes(refType.get(id) ?? ''),
    marker: (id: string) => !h.marker.includes(id),
    overdue: !h.marker.includes(OVERDUE),
    today: !h.marker.includes(TODAY),
  };
}
