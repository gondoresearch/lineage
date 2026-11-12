// Lane order: grouped by group (file order), gap between groups; within a
// group depth-first over the fork tree, so a fork sits directly below its
// origin. Roots and siblings follow the project list order in the file (the
// manual order, changed by dragging lane labels).
import type { Index } from './model';

export const LANE_H = 34;
/** heading rows in the label column */
export const GROUP_HEAD_H = 22;
export const DOMAIN_HEAD_H = 26;
/** gaps before a group (after the first) and before a domain block */
export const GROUP_GAP = 14;
export const DOMAIN_GAP = 18;

export interface Lane {
  project: string;
  group: string;
  depth: number;
  /** lane centre */
  y: number;
}

/** A group's area: its heading row and its lanes. */
export interface GroupBand {
  group: string;
  domain: string | null;
  y0: number;
  y1: number;
}

/** A heading row in the label column (domain, or group within it). */
export interface Header {
  kind: 'domain' | 'group';
  id: string;
  /** row centre */
  y: number;
  /** the group's domain (null for a domain row or a group without one) */
  domain: string | null;
}

export interface LaneLayout {
  lanes: Lane[];
  bands: GroupBand[];
  headers: Header[];
  height: number;
  y: Map<string, number>;
}

/**
 * Groups in display order: those without a domain first (in file order),
 * then each domain in domain order, with its groups in file order.
 */
export function groupOrder(idx: Index): { domain: string | null; groups: string[] }[] {
  const domains = idx.ws.domains ?? [];
  const known = new Set(domains.map((d) => d.id));
  const blocks: { domain: string | null; groups: string[] }[] = [
    { domain: null, groups: idx.ws.groups.filter((g) => !g.domain || !known.has(g.domain)).map((g) => g.id) },
  ];
  for (const d of domains) blocks.push({ domain: d.id, groups: idx.ws.groups.filter((g) => g.domain === d.id).map((g) => g.id) });
  return blocks;
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
  const headers: Header[] = [];
  let top = 0;
  for (const block of groupOrder(idx)) {
    const shown = block.groups.filter((gid) => projects.some((p) => p.group === gid));
    if (!shown.length) continue; // empty domains (or all filtered out) take no space
    if (block.domain) {
      if (top > 0) top += DOMAIN_GAP;
      headers.push({ kind: 'domain', id: block.domain, y: top + DOMAIN_HEAD_H / 2, domain: null });
      top += DOMAIN_HEAD_H;
    }
    shown.forEach((gid, gi) => {
      const members = projects.filter((p) => p.group === gid).map((p) => p.id);
      const inGroup = new Set(members);
      const children = new Map<string, string[]>();
      const roots: string[] = [];
      for (const pid of members) {
        const parent = originProject(pid);
        if (parent && inGroup.has(parent)) children.set(parent, [...(children.get(parent) ?? []), pid]);
        else roots.push(pid);
      }
      if (gi > 0 || (!block.domain && top > 0)) top += GROUP_GAP;
      const y0 = top;
      headers.push({ kind: 'group', id: gid, y: top + GROUP_HEAD_H / 2, domain: block.domain });
      top += GROUP_HEAD_H;
      const visit = (pid: string, depth: number) => {
        lanes.push({ project: pid, group: gid, depth, y: top + LANE_H / 2 });
        top += LANE_H;
        for (const c of (children.get(pid) ?? []).sort(byOrder)) visit(c, depth + 1);
      };
      for (const r of roots.sort(byOrder)) visit(r, 0);
      bands.push({ group: gid, domain: block.domain, y0, y1: top });
    });
  }
  return { lanes, bands, headers, height: top, y: new Map(lanes.map((l) => [l.project, l.y])) };
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

export function nearestSlot<T extends { y: number }>(slots: T[], y: number): T | null {
  let best: T | null = null;
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

// ------------------------------------------------------------------ moving groups and domains

/** A place a dragged group can be dropped: before a group, or at the end of a domain's groups. */
export interface GroupSlot {
  /** the domain the group lands in (null: no domain) */
  domain: string | null;
  /** group whose block the dropped one goes in front of; null = end of the domain */
  before: string | null;
  /** y of the insertion line (lane coordinates) */
  y: number;
}

/** Group drop lines. Only groups with a visible lane have a place on screen. */
export function groupSlots(layout: LaneLayout): GroupSlot[] {
  const out: GroupSlot[] = [];
  const domains = new Set<string | null>(layout.bands.map((b) => b.domain));
  // an empty "no domain" block has no band: allow dropping at the very top
  if (!domains.has(null)) out.push({ domain: null, before: null, y: 0 });
  for (const d of domains) {
    const bands = layout.bands.filter((b) => b.domain === d);
    for (const b of bands) out.push({ domain: d, before: b.group, y: b.y0 });
    out.push({ domain: d, before: null, y: bands[bands.length - 1].y1 });
  }
  return out;
}

export interface MovableGroup {
  id: string;
  domain: string | null;
}

/**
 * The PATCH that moves group `gid` to `slot`: its domain (only if it changes) and
 * its index in the group list (counted without the group itself), or null if
 * nothing would change. Hidden groups keep their place: the index is computed
 * in the full list.
 */
export function groupMoveRequest(
  groups: MovableGroup[],
  gid: string,
  slot: GroupSlot,
): { domain?: string | null; position: number } | null {
  const me = groups.find((g) => g.id === gid);
  if (!me) return null;
  const rest = groups.filter((g) => g.id !== gid);
  let position: number;
  if (slot.before) {
    position = rest.findIndex((g) => g.id === slot.before);
    if (position < 0) return null;
  } else {
    position = rest.findLastIndex((g) => g.domain === slot.domain) + 1;
    if (position === 0) position = rest.length; // the domain has no group yet
  }
  const order = (l: MovableGroup[], d: string | null) => l.filter((g) => g.domain === d).map((g) => g.id).join();
  const next = [...rest.slice(0, position), { ...me, domain: slot.domain }, ...rest.slice(position)];
  if (slot.domain === me.domain && order(next, slot.domain) === order(groups, slot.domain)) return null;
  return slot.domain === me.domain ? { position } : { domain: slot.domain, position };
}

/** A place a dragged domain can be dropped: before a domain, or after the last one shown. */
export interface DomainSlot {
  /** domain the dropped one goes in front of; null = after the last shown domain */
  before: string | null;
  y: number;
}

export function domainSlots(layout: LaneLayout): DomainSlot[] {
  const heads = layout.headers.filter((h) => h.kind === 'domain');
  return [...heads.map((h) => ({ before: h.id, y: h.y - DOMAIN_HEAD_H / 2 })), { before: null, y: layout.height }];
}

/** The PATCH that moves domain `did` to `slot`, or null if the order stays. */
export function domainMoveRequest(
  domains: { id: string }[],
  shown: string[],
  did: string,
  slot: DomainSlot,
): { position: number } | null {
  const rest = domains.filter((d) => d.id !== did);
  let position: number;
  if (slot.before) {
    position = rest.findIndex((d) => d.id === slot.before);
    if (position < 0) return null;
  } else {
    const last = rest.findLastIndex((d) => shown.includes(d.id));
    position = last + 1;
  }
  const next = [...rest.slice(0, position).map((d) => d.id), did, ...rest.slice(position).map((d) => d.id)];
  if (next.join() === domains.map((d) => d.id).join()) return null;
  return { position };
}
