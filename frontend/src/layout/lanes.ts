// Lane order: grouped by group (file order), gap between groups; within a
// group depth-first over the fork tree, so a fork sits directly below its
// origin. Roots and siblings follow the project list order in the file (the
// manual order, changed by dragging lane labels).
import type { Index } from './model';

export const LANE_H = 34;
export const GROUP_GAP = 22;

export interface Lane {
  project: string;
  group: string;
  depth: number;
  /** lane centre */
  y: number;
}

export interface GroupBand {
  group: string;
  y0: number;
  y1: number;
}

export interface LaneLayout {
  lanes: Lane[];
  bands: GroupBand[];
  height: number;
  y: Map<string, number>;
}

export function layoutLanes(idx: Index, visible: (pid: string) => boolean = () => true): LaneLayout {
  const projects = idx.ws.projects.filter((p) => visible(p.id));
  const order = new Map(idx.ws.projects.map((p, i) => [p.id, i]));
  const byOrder = (a: string, b: string) => order.get(a)! - order.get(b)!;
  const originProject = (pid: string): string | null => {
    const from = idx.projects.get(pid)?.from;
    return from ? (idx.milestones.get(from)?.project ?? null) : null;
  };

  const lanes: Lane[] = [];
  const bands: GroupBand[] = [];
  let top = 0;
  for (const g of idx.ws.groups) {
    const members = projects.filter((p) => p.group === g.id).map((p) => p.id);
    if (!members.length) continue;
    const inGroup = new Set(members);
    const children = new Map<string, string[]>();
    const roots: string[] = [];
    for (const pid of members) {
      const parent = originProject(pid);
      if (parent && inGroup.has(parent)) {
        children.set(parent, [...(children.get(parent) ?? []), pid]);
      } else {
        roots.push(pid);
      }
    }
    if (bands.length) top += GROUP_GAP;
    const y0 = top;
    const visit = (pid: string, depth: number) => {
      lanes.push({ project: pid, group: g.id, depth, y: top + LANE_H / 2 });
      top += LANE_H;
      for (const c of (children.get(pid) ?? []).sort(byOrder)) visit(c, depth + 1);
    };
    for (const r of roots.sort(byOrder)) visit(r, 0);
    bands.push({ group: g.id, y0, y1: top });
  }
  return { lanes, bands, height: top, y: new Map(lanes.map((l) => [l.project, l.y])) };
}

// ------------------------------------------------------------------ moving lanes

/** A place a dragged lane can be dropped: before a lane, or at the end of a group. */
export interface DropSlot {
  group: string;
  /** project whose lane the dropped one goes in front of; null = end of the group */
  before: string | null;
  /** y of the insertion line (lane coordinates) */
  y: number;
}

export function dropSlots(layout: LaneLayout): DropSlot[] {
  const out: DropSlot[] = [];
  for (const b of layout.bands) {
    for (const l of layout.lanes) {
      if (l.group === b.group) out.push({ group: b.group, before: l.project, y: l.y - LANE_H / 2 });
    }
    out.push({ group: b.group, before: null, y: b.y1 });
  }
  return out;
}

export function nearestSlot(slots: DropSlot[], y: number): DropSlot | null {
  let best: DropSlot | null = null;
  for (const s of slots) if (!best || Math.abs(s.y - y) < Math.abs(best.y - y)) best = s;
  return best;
}

export interface MovableProject {
  id: string;
  group: string;
  /** project the fork originates from, if any */
  origin: string | null;
}

/**
 * The PATCH that moves project `pid` to `slot`: its group and its index in the
 * project list (counted without the project itself), or null if the visible
 * order would not change.
 *
 * The project keeps its place in the fork tree (a fork stays under its origin
 * when both are in the same group), so it is placed among its future siblings:
 * before the first sibling lane at or below the drop line, else after the last
 * sibling. Its forks move with it.
 */
export function moveRequest(
  projects: MovableProject[],
  layout: LaneLayout,
  pid: string,
  slot: DropSlot,
): { group: string; position: number } | null {
  const current = projects.findIndex((p) => p.id === pid);
  if (current < 0) return null;
  const me = projects[current];
  const groupOf = new Map(projects.map((p) => [p.id, p.group]));
  const parentIn = (p: MovableProject, group: string) => (p.origin && groupOf.get(p.origin) === group ? p.origin : null);

  const parent = parentIn(me, slot.group);
  const siblings = projects.filter((p) => p.id !== pid && p.group === slot.group && parentIn(p, slot.group) === parent);
  const laneIndex = new Map(layout.lanes.map((l, i) => [l.project, i]));
  let slotIndex: number;
  if (slot.before) slotIndex = laneIndex.get(slot.before) ?? Infinity;
  else {
    const last = layout.lanes.findLastIndex((l) => l.group === slot.group);
    slotIndex = last + 1;
  }
  const next = siblings
    .filter((p) => (laneIndex.get(p.id) ?? -1) >= slotIndex)
    .sort((a, b) => laneIndex.get(a.id)! - laneIndex.get(b.id)!)[0];

  // No-op if the group is unchanged and the rank among siblings stays the same.
  const listIndex = new Map(projects.map((p, i) => [p.id, i]));
  const byList = [...siblings].sort((a, b) => listIndex.get(a.id)! - listIndex.get(b.id)!);
  const newRank = next ? byList.indexOf(next) : byList.length;
  const oldRank = byList.filter((p) => listIndex.get(p.id)! < current).length;
  if (slot.group === me.group && newRank === oldRank) return null;

  const rest = projects.filter((p) => p.id !== pid);
  let position: number;
  if (next) position = rest.indexOf(next);
  else if (byList.length) position = rest.indexOf(byList[byList.length - 1]) + 1;
  else position = current;
  return { group: slot.group, position };
}

/**
 * Projects drawn under `pid`: its forks in the same group, their forks, and so
 * on. They move along when the project changes group (the backend does the same).
 */
export function laneSubtree(projects: MovableProject[], pid: string): string[] {
  const group = projects.find((p) => p.id === pid)?.group;
  const out: string[] = [];
  const frontier = [pid];
  while (frontier.length) {
    const parent = frontier.pop()!;
    for (const p of projects) {
      if (p.origin === parent && p.group === group && !out.includes(p.id)) {
        out.push(p.id);
        frontier.push(p.id);
      }
    }
  }
  return out;
}
