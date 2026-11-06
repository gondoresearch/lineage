// Hover highlighting: transitive ancestors and descendants (over in-project
// order, forks, merges and directed references) plus undirected reference partners.
import type { Workspace } from '../api/client';

interface Graph {
  up: Map<string, Set<string>>;
  down: Map<string, Set<string>>;
  partners: Map<string, Set<string>>;
}

function emptyGraph(): Graph {
  return { up: new Map(), down: new Map(), partners: new Map() };
}

function add(m: Map<string, Set<string>>, k: string, v: string) {
  if (!m.has(k)) m.set(k, new Set());
  m.get(k)!.add(v);
}

/** Edge from ancestor `a` to descendant `b`. */
function link(g: Graph, a: string, b: string) {
  if (a === b) return;
  add(g.down, a, b);
  add(g.up, b, a);
}

function closure(g: Graph, start: string): Set<string> {
  const out = new Set([start]);
  for (const dir of [g.up, g.down]) {
    const stack = [start];
    const seen = new Set([start]);
    while (stack.length) {
      for (const n of dir.get(stack.pop()!) ?? []) {
        if (!seen.has(n)) {
          seen.add(n);
          out.add(n);
          stack.push(n);
        }
      }
    }
  }
  for (const p of g.partners.get(start) ?? []) out.add(p);
  return out;
}

function referenceLinks(ws: Workspace, g: Graph, key: (milestone: string) => string) {
  const directed = new Map(ws.reftypes.map((t) => [t.id, t.directed]));
  for (const r of ws.references) {
    const a = key(r.to);
    const b = key(r.from);
    if (directed.get(r.type)) link(g, a, b); // `from` builds on `to`
    else if (a !== b) {
      add(g.partners, a, b);
      add(g.partners, b, a);
    }
  }
}

/** Milestones related to milestone `id` (including itself). */
export function relatedMilestones(ws: Workspace, id: string): Set<string> {
  const g = emptyGraph();
  for (const [child, parents] of Object.entries(ws.derived.parents)) for (const p of parents) link(g, p, child);
  referenceLinks(ws, g, (m) => m);
  return closure(g, id);
}

/** Projects related to project `pid` (including itself), at project level. */
export function relatedProjects(ws: Workspace, pid: string): Set<string> {
  const projectOf = new Map(ws.milestones.map((m) => [m.id, m.project]));
  const g = emptyGraph();
  for (const p of ws.projects) if (p.from) link(g, projectOf.get(p.from)!, p.id);
  for (const m of ws.milestones) for (const s of m.merges ?? []) link(g, projectOf.get(s)!, m.project);
  referenceLinks(ws, g, (m) => projectOf.get(m)!);
  return closure(g, pid);
}
