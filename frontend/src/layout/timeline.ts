// Timeline geometry in screen coordinates (no DOM).
import type { Milestone, Schemas, State } from '../api/client';
import { colors } from './colors';
import type { LaneLayout } from './lanes';
import { projectMilestones, type Index } from './model';
import type { XScale, ZoomT } from './xscale';

/** Default node radius; a kind's `size` scales it. Lines stop at a node's radius. */
export const R = 6;

export type LineStyle = Schemas['State']['line'];

export interface Node {
  id: string;
  project: string;
  x: number;
  y: number;
  /** radius: R × the kind's size; lines stop this far from the centre */
  r: number;
  shape: string;
  color: string;
  planned: boolean;
  overdue: boolean;
  /** user markers shown as badges */
  markers: { id: string; icon: string; color: string; name: string }[];
}

/** Optional text drawn with a line (only when its state / reference sets one). */
export interface LineText {
  text: string;
  x: number;
  y: number;
  anchor: 'start' | 'middle' | 'end';
  /** 'central' for text sitting on the line (middle) */
  baseline: 'auto' | 'central';
  /** rotation in degrees about (x, y); 0 = horizontal */
  angle: number;
  /** font size in px */
  size: number;
}

/** Approximate width of line text at a font size. */
export const textWidth = (t: string, size = 10) => t.length * size * 0.56;

type Align = 'left' | 'center' | 'right';
type Position = 'above' | 'middle' | 'below';

/** Vertical placement relative to a line of thickness `w` at height `y`. */
function textY(y: number, w: number, pos: Position, size: number): { y: number; baseline: 'auto' | 'central' } {
  return { y: y + textOffset(w, pos, size), baseline: pos === 'middle' ? 'central' : 'auto' };
}

/** Distance of the text baseline from the line, perpendicular to it (negative = above). */
function textOffset(w: number, pos: Position, size: number): number {
  return pos === 'middle' ? 0 : pos === 'above' ? -(w / 2 + 3) : w / 2 + size;
}

/**
 * Text at point `at` of a line whose direction there is `tangent`. Horizontal:
 * always level. Along: rotated to follow the line, flipped so it never reads
 * upside down; above / below are then relative to the line itself.
 */
export function placeText(
  text: string,
  at: { x: number; y: number },
  tangent: { x: number; y: number },
  w: number,
  pos: Position,
  orientation: 'horizontal' | 'along',
  size = 10,
): LineText {
  let angle = 0;
  if (orientation === 'along' && (tangent.x || tangent.y)) {
    angle = (Math.atan2(tangent.y, tangent.x) * 180) / Math.PI;
    if (angle > 90) angle -= 180;
    if (angle < -90) angle += 180;
  }
  const off = textOffset(w, pos, size);
  const rad = (angle * Math.PI) / 180;
  // The offset (0, off) in the text's rotated frame.
  return {
    text,
    x: at.x - off * Math.sin(rad),
    y: at.y + off * Math.cos(rad),
    anchor: 'middle',
    baseline: pos === 'middle' ? 'central' : 'auto',
    angle,
    size,
  };
}

/** Text on a horizontal lane segment; null if it does not fit. */
export function segmentText(
  text: string,
  x1: number,
  x2: number,
  y: number,
  w: number,
  align: Align,
  pos: Position,
  size = 10,
): LineText | null {
  if (!text || textWidth(text, size) + 8 > x2 - x1) return null;
  const x = align === 'left' ? x1 + 4 : align === 'right' ? x2 - 4 : (x1 + x2) / 2;
  const anchor = align === 'left' ? 'start' : align === 'right' ? 'end' : 'middle';
  return { text, x, anchor, ...textY(y, w, pos, size), angle: 0, size };
}

/** Derivative at fraction t of a cubic Bézier (the tangent direction). */
function bezierSlope(p0: number, p1: number, p2: number, p3: number, t: number): number {
  const u = 1 - t;
  return 3 * u * u * (p1 - p0) + 6 * u * t * (p2 - p1) + 3 * t * t * (p3 - p2);
}

/** Point at fraction t along a cubic Bézier. */
function bezier(p0: number, p1: number, p2: number, p3: number, t: number): number {
  const u = 1 - t;
  return u * u * u * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t * t * t * p3;
}

export interface Segment {
  project: string;
  /** milestone whose state styles the segment */
  from: string;
  /** milestone it leads to; null for the line from the head to today */
  to: string | null;
  x1: number;
  x2: number;
  y: number;
  line: LineStyle;
  color: string;
  /** the state's line opacity (planned parts are faded on top of this) */
  opacity: number;
  /** line thickness */
  width: number;
  faded: boolean;
  label: LineText | null;
}

export interface Edge {
  kind: 'fork' | 'merge' | 'reference';
  /** project id (fork), merging milestone id (merge) or reference id */
  id: string;
  from: string;
  to: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  path: string;
  color: string;
  line: LineStyle;
  /** the reference type's line opacity; 1 for forks and merges */
  opacity: number;
  /** line thickness */
  width: number;
  arrow: boolean;
  /** the reference's own text, if set */
  label: LineText | null;
}

export interface TimelineGeometry {
  nodes: Node[];
  segments: Segment[];
  edges: Edge[];
  todayX: number;
}

/**
 * Rank of each milestone among the milestones of its day, across all projects: its depth
 * along history links (previous milestone in the project, fork origin, merge sources)
 * that stay within the same day. A same-day fork therefore sits right of its origin, and
 * a same-day merge right of what it merges; unrelated same-day milestones share a rank.
 */
export function ranks(idx: Index): Map<string, number> {
  const parents = new Map<string, string[]>();
  for (const p of idx.ws.projects) {
    const ms = projectMilestones(idx, p.id);
    ms.forEach((m, i) => {
      const prev = i > 0 ? [ms[i - 1].id] : p.from ? [p.from] : [];
      parents.set(m.id, [...prev, ...(m.merges ?? [])]);
    });
  }
  const date = new Map(idx.ws.milestones.map((m) => [m.id, m.date]));
  const out = new Map<string, number>();
  const visiting = new Set<string>();
  const rank = (id: string): number => {
    const known = out.get(id);
    if (known !== undefined) return known;
    if (visiting.has(id)) return 0; // the backend rejects cycles; just never loop
    visiting.add(id);
    let r = 0;
    for (const p of parents.get(id) ?? []) if (date.get(p) === date.get(id)) r = Math.max(r, rank(p) + 1);
    visiting.delete(id);
    out.set(id, r);
    return r;
  };
  for (const m of idx.ws.milestones) rank(m.id);
  return out;
}

const r2 = (v: number) => Math.round(v * 100) / 100;

/** Curve leaving (x1,y1) vertically and entering (x2,y2) horizontally. */
function elbow(x1: number, y1: number, x2: number, y2: number): string {
  return `M${r2(x1)},${r2(y1)} C${r2(x1)},${r2(y2)} ${r2(x1)},${r2(y2)} ${r2(x2)},${r2(y2)}`;
}

/** Endpoints for a fork/merge edge between two nodes in different lanes. */
function elbowEnds(a: Node, b: Node) {
  const dir = b.y > a.y ? 1 : -1;
  const x1 = a.x;
  const y1 = a.y + dir * a.r;
  if (b.x - b.r > a.x + 1) return { x1, y1, x2: b.x - b.r, y2: b.y };
  // Target not to the right of the source: enter from above/below instead.
  return { x1, y1, x2: b.x, y2: b.y - dir * b.r };
}

export function computeTimeline(
  idx: Index,
  lanes: LaneLayout,
  xs: XScale,
  t: ZoomT,
  today: string,
): TimelineGeometry {
  const c = colors(idx);
  const rank = ranks(idx);
  const todayX = xs.today(t);
  const nodes: Node[] = [];
  const nodeById = new Map<string, Node>();
  const segments: Segment[] = [];
  const edges: Edge[] = [];
  const stateOf = (m: Milestone) => (m.state ? idx.states.get(m.state) : undefined);
  // A lane line's look: the milestone's own settings for the line after it, else its state's.
  const lineOf = (m: Milestone): LineStyle => m.line_pattern ?? stateOf(m)?.line ?? 'solid';

  for (const lane of lanes.lanes) {
    const ms = projectMilestones(idx, lane.project);
    const laneNodes = ms.map((m) => {
      const n: Node = {
        id: m.id,
        project: m.project,
        x: xs.x(m.date, rank.get(m.id) ?? 0, t),
        y: lane.y,
        r: R * (idx.kinds.get(m.kind)?.size ?? 1),
        shape: idx.kinds.get(m.kind)?.shape ?? 'open-circle',
        color: c.milestone(m),
        planned: !!m.planned,
        overdue: !!m.planned && m.date < today,
        markers: (m.markers ?? []).flatMap((id) => {
          const mk = idx.markers.get(id);
          return mk ? [{ id, icon: mk.icon, color: c.marker(mk), name: mk.name }] : [];
        }),
      };
      nodes.push(n);
      nodeById.set(m.id, n);
      return n;
    });

    // The milestone's own line text, else its state's default text.
    const lineText = (m: Milestone, st: State | undefined, x1: number, x2: number, y: number): LineText | null => {
      const w = m.line_width ?? st?.line_width ?? 2.5;
      if (m.line_text) {
        return segmentText(m.line_text, x1, x2, y, w, m.line_text_align ?? 'center', m.line_text_position ?? 'above', m.line_text_size ?? 10);
      }
      if (st?.text) return segmentText(st.text, x1, x2, y, w, st.text_align ?? 'center', st.text_position ?? 'above', st.text_size ?? 10);
      return null;
    };

    const seg = (from: Milestone, to: Milestone | null, x1: number, x2: number, faded: boolean) => {
      if (x2 - x1 > 0.5) {
        const st = stateOf(from);
        segments.push({
          project: lane.project,
          from: from.id,
          to: to?.id ?? null,
          x1,
          x2,
          y: lane.y,
          line: lineOf(from),
          color: c.segment(from),
          opacity: from.line_opacity ?? st?.opacity ?? 1,
          width: from.line_width ?? st?.line_width ?? 2.5,
          faded,
          label: lineText(from, st, x1, x2, lane.y),
        });
      }
    };

    const d = idx.ws.derived.projects[lane.project];
    const headIdx = d?.head ? ms.findIndex((m) => m.id === d.head) : -1;
    const head = headIdx >= 0 ? ms[headIdx] : undefined;
    // Head → today, in the head's state style, if someone is expected to act.
    const toToday = !!head && !d.merged && !d.closed && head.date < today && stateOf(head)?.waiting_on !== 'nobody';
    const closes = (m: Milestone) => !!idx.kinds.get(m.kind)?.closes;

    for (let i = 0; i + 1 < ms.length; i++) {
      const a = ms[i];
      const b = ms[i + 1];
      // Covered by the head → today line below.
      if (toToday && i >= headIdx && b.date < today) continue;
      // A closing milestone ends the lane: no line after it.
      if (closes(a)) continue;
      let x1 = laneNodes[i].x + laneNodes[i].r;
      // Before a future planned milestone, the faded part starts at today.
      if (b.planned && b.date > today && !(a.planned && a.date > today)) x1 = Math.max(x1, todayX);
      seg(a, b, x1, laneNodes[i + 1].x - laneNodes[i + 1].r, !!(a.planned || b.planned));
    }

    if (toToday) {
      // Broken around overdue planned milestones so the line stops at their edges.
      let x1 = laneNodes[headIdx].x + laneNodes[headIdx].r;
      for (let i = headIdx + 1; i < ms.length && ms[i].date < today; i++) {
        seg(head!, null, x1, laneNodes[i].x - laneNodes[i].r, false);
        x1 = laneNodes[i].x + laneNodes[i].r;
      }
      seg(head!, null, x1, todayX, false);
    }
  }

  // Forks: origin milestone → project's first milestone.
  for (const p of idx.ws.projects) {
    if (!p.from) continue;
    const firstId = idx.ws.derived.projects[p.id]?.milestones[0];
    const a = nodeById.get(p.from);
    const b = firstId ? nodeById.get(firstId) : undefined;
    if (!a || !b) continue;
    const e = elbowEnds(a, b);
    edges.push({ kind: 'fork', id: p.id, from: a.id, to: b.id, ...e, path: elbow(e.x1, e.y1, e.x2, e.y2), color: c.fork(p), line: 'solid', opacity: 1, width: idx.ws.settings.fork_width ?? 1.8, arrow: false, label: null });
  }

  // Merges: source milestone → merging milestone.
  for (const m of idx.ws.milestones) {
    for (const src of m.merges ?? []) {
      const a = nodeById.get(src);
      const b = nodeById.get(m.id);
      if (!a || !b) continue;
      const e = elbowEnds(a, b);
      edges.push({ kind: 'merge', id: m.id, from: a.id, to: b.id, ...e, path: elbow(e.x1, e.y1, e.x2, e.y2), color: c.merge(idx.milestones.get(src)!), line: 'solid', opacity: 1, width: idx.ws.settings.merge_width ?? 1.8, arrow: false, label: null });
    }
  }

  // References: from → to; the arrowhead (if directed) points at `to`.
  for (const r of idx.ws.references) {
    const a = nodeById.get(r.from);
    const b = nodeById.get(r.to);
    const rt = idx.reftypes.get(r.type);
    if (!a || !b || !rt) continue;
    let x1: number, y1: number, x2: number, y2: number, path: string;
    // Where along the line the text goes: near `from`, the middle, or near `to`.
    const t = r.text_align === 'left' ? 0.15 : r.text_align === 'right' ? 0.85 : 0.5;
    let at: { x: number; y: number };
    let tangent: { x: number; y: number };
    if (Math.abs(a.y - b.y) < 0.5) {
      // Same lane: arc above it, leaving and entering through the node tops.
      [x1, y1, x2, y2] = [a.x, a.y - a.r, b.x, b.y - b.r];
      const lift = Math.min(28, 10 + Math.abs(b.x - a.x) / 6);
      path = `M${r2(x1)},${r2(y1)} C${r2(x1)},${r2(y1 - lift)} ${r2(x2)},${r2(y2 - lift)} ${r2(x2)},${r2(y2)}`;
      at = { x: bezier(x1, x1, x2, x2, t), y: bezier(y1, y1 - lift, y2 - lift, y2, t) };
      tangent = { x: bezierSlope(x1, x1, x2, x2, t), y: bezierSlope(y1, y1 - lift, y2 - lift, y2, t) };
    } else {
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const len = Math.hypot(dx, dy) || 1;
      [x1, y1, x2, y2] = [a.x + (dx / len) * a.r, a.y + (dy / len) * a.r, b.x - (dx / len) * b.r, b.y - (dy / len) * b.r];
      path = `M${r2(x1)},${r2(y1)} L${r2(x2)},${r2(y2)}`;
      at = { x: x1 + (x2 - x1) * t, y: y1 + (y2 - y1) * t };
      tangent = { x: x2 - x1, y: y2 - y1 };
    }
    const width = rt.line_width ?? 1.4;
    const label: LineText | null = r.text
      ? placeText(r.text, at, tangent, width, r.text_position ?? 'above', r.text_orientation ?? 'horizontal', r.text_size ?? 10)
      : null;
    edges.push({ kind: 'reference', id: r.id, from: a.id, to: b.id, x1, y1, x2, y2, path, color: c.reference(r), line: rt.line, opacity: rt.opacity ?? 1, width, arrow: rt.directed, label });
  }

  return { nodes, segments, edges, todayX };
}
