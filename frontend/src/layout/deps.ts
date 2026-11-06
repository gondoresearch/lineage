// Dependencies view: projects as nodes, forks / merges / references aggregated
// to project level, laid out with dagre (rankdir BT: earlier work at the bottom).
import { Graph, layout } from '@dagrejs/dagre';
import type { Milestone } from '../api/client';
import { colors } from './colors';
import type { Index } from './model';

export interface DepEdge {
  kind: 'fork' | 'merge' | 'reference';
  /** project ids; for references `from` builds on / refers to `to` */
  from: string;
  to: string;
  /** reference type id (references only) */
  type: string | null;
  color: string;
  line: string;
  opacity: number;
  width: number;
  arrow: boolean;
  /** how many underlying forks / merges / references */
  count: number;
}

/** Forks, merges and references aggregated per project pair (and per reference type). */
export function projectEdges(idx: Index, visible: (pid: string) => boolean = () => true): DepEdge[] {
  const c = colors(idx);
  const out = new Map<string, DepEdge>();
  const projectOf = (m: string) => idx.milestones.get(m)?.project;
  const put = (key: string, e: Omit<DepEdge, 'count'>) => {
    if (e.from === e.to || !visible(e.from) || !visible(e.to)) return;
    const prev = out.get(key);
    if (prev) prev.count++;
    else out.set(key, { ...e, count: 1 });
  };
  for (const p of idx.ws.projects) {
    const origin = p.from ? projectOf(p.from) : undefined;
    if (origin) put(`fork|${origin}|${p.id}`, { kind: 'fork', from: origin, to: p.id, type: null, color: c.fork(p), line: 'solid', opacity: 1, width: idx.ws.settings.fork_width ?? 1.8, arrow: false });
  }
  for (const m of idx.ws.milestones) {
    for (const s of m.merges ?? []) {
      const src = projectOf(s);
      const source = idx.milestones.get(s) as Milestone;
      if (src) put(`merge|${src}|${m.project}`, { kind: 'merge', from: src, to: m.project, type: null, color: c.merge(source), line: 'solid', opacity: 1, width: idx.ws.settings.merge_width ?? 1.8, arrow: false });
    }
  }
  for (const r of idx.ws.references) {
    const a = projectOf(r.from);
    const b = projectOf(r.to);
    const rt = idx.reftypes.get(r.type);
    if (a && b && rt) {
      put(`ref|${r.type}|${a}|${b}`, { kind: 'reference', from: a, to: b, type: r.type, color: c.reftype(r.type), line: rt.line, opacity: rt.opacity ?? 1, width: rt.line_width ?? 1.4, arrow: rt.directed });
    }
  }
  return [...out.values()];
}

export interface DepNode {
  id: string;
  title: string;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
}

export interface DepLayout {
  nodes: DepNode[];
  edges: (DepEdge & { points: { x: number; y: number }[] })[];
  width: number;
  height: number;
}

export const NODE_H = 30;
export const CHAR_W = 7.2;

export function labelOf(title: string): string {
  return title.length > 34 ? title.slice(0, 33) + '…' : title;
}

export function layoutDeps(idx: Index, visible: (pid: string) => boolean = () => true): DepLayout {
  const c = colors(idx);
  const g = new Graph({ multigraph: true });
  g.setGraph({ rankdir: 'BT', nodesep: 28, ranksep: 54, edgesep: 14, marginx: 12, marginy: 12 });
  g.setDefaultEdgeLabel(() => ({}));
  const projects = idx.ws.projects.filter((p) => visible(p.id));
  for (const p of projects) g.setNode(p.id, { width: labelOf(p.title).length * CHAR_W + 28, height: NODE_H });

  const edges = projectEdges(idx, visible);
  edges.forEach((e, i) => {
    // Layout direction: earlier work → later work, so the earlier one ranks lower (bottom).
    const [v, w] = e.kind === 'reference' && e.arrow ? [e.to, e.from] : [e.from, e.to];
    g.setEdge(v, w, {}, `e${i}`);
  });
  layout(g);

  const nodes: DepNode[] = projects.map((p) => {
    const n = g.node(p.id);
    return { id: p.id, title: p.title, x: n.x, y: n.y, width: n.width, height: n.height, color: c.project(p) };
  });
  const laidOut = edges.map((e, i) => {
    const [v, w] = e.kind === 'reference' && e.arrow ? [e.to, e.from] : [e.from, e.to];
    const pts = (g.edge({ v, w, name: `e${i}` }).points ?? []) as { x: number; y: number }[];
    // Draw references from `from` to `to`, so a directed one's arrowhead sits at `to`.
    return { ...e, points: e.kind === 'reference' && e.arrow ? [...pts].reverse() : pts };
  });
  const gl = g.graph();
  return { nodes, edges: laidOut, width: gl.width ?? 0, height: gl.height ?? 0 };
}
