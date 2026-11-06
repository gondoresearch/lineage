// Filters, status board, hover highlighting and the dependencies layout.
import { describe, expect, it } from 'vitest';
import { layoutDeps, projectEdges } from './deps';
import { makeWs } from './fixture';
import { isInactive, NO_FILTERS, projectFilter } from './filters';
import { relatedMilestones, relatedProjects } from './highlight';
import { indexWorkspace } from './model';
import { formatDays, statusBoard } from './status';

const TODAY = '2026-01-01';

// g1: a → (fork) b → (fork) c ; d merges b ; e builds on a ; f companion of a ; g all planned
const ws = makeWs({
  groups: [{ id: 'g1' }, { id: 'g2' }],
  projects: [
    { id: 'a', group: 'g1' },
    { id: 'b', group: 'g1', from: 'a.1' },
    { id: 'c', group: 'g1', from: 'b.1' },
    { id: 'd', group: 'g2' },
    { id: 'e', group: 'g2' },
    { id: 'f', group: 'g2' },
    { id: 'g', group: 'g2' },
  ],
  milestones: [
    { id: 'a.1', date: '2025-01-01', state: 'drafting' },
    { id: 'a.2', date: '2025-06-01', state: 'review' },
    { id: 'b.1', date: '2025-02-01', state: 'drafting' },
    { id: 'b.2', date: '2025-03-01', state: 'done' },
    { id: 'c.1', date: '2025-04-01', state: 'drafting' },
    { id: 'c.2', date: '2025-12-01', state: 'review', planned: true }, // overdue
    { id: 'c.3', date: '2026-03-01', state: 'review', planned: true },
    { id: 'd.1', date: '2025-01-15', state: 'drafting' },
    { id: 'd.2', date: '2025-04-01', state: 'review', merges: ['b.2'] },
    { id: 'e.1', date: '2025-07-01', state: 'drafting' },
    { id: 'f.1', date: '2025-08-01', state: 'done' },
    { id: 'g.1', date: '2026-05-01', state: 'drafting', planned: true },
  ],
  references: [
    { id: 'r1', type: 'builds-on', from: 'e.1', to: 'a.2', color: null, description: '' },
    { id: 'r2', type: 'companion', from: 'f.1', to: 'a.1', color: null, description: '' },
  ],
});
const idx = indexWorkspace(ws);

describe('filters', () => {
  it('inactive = waiting on nobody, or no head yet', () => {
    expect(isInactive(ws, 'f')).toBe(true); // done
    expect(isInactive(ws, 'g')).toBe(true); // only planned milestones
    expect(isInactive(ws, 'a')).toBe(false);
  });

  it('filters by group, current state and inactivity', () => {
    const keep = (f: Partial<typeof NO_FILTERS>) => ws.projects.map((p) => p.id).filter(projectFilter(ws, { ...NO_FILTERS, ...f }));
    expect(keep({})).toEqual(['a', 'b', 'c', 'd', 'e', 'f', 'g']);
    expect(keep({ groups: ['g1'] })).toEqual(['a', 'b', 'c']);
    expect(keep({ states: ['review'] })).toEqual(['a', 'd']);
    expect(keep({ hideInactive: true })).toEqual(['a', 'c', 'd', 'e']);
    expect(keep({ groups: ['g2'], hideInactive: true })).toEqual(['d', 'e']);
  });
});

describe('status board', () => {
  const board = statusBoard(ws, TODAY);

  it('puts cards in columns by who the current state waits on', () => {
    expect(board.me.map((c) => c.project).sort()).toEqual(['c', 'e']);
    expect(board.others.map((c) => c.project).sort()).toEqual(['a', 'd']);
    expect(board.inactive.map((c) => c.project).sort()).toEqual(['b', 'f', 'g']);
  });

  it('sorts by time in state, longest first; no head last', () => {
    expect(board.me.map((c) => c.project)).toEqual(['c', 'e']); // since Apr vs Jul
    expect(board.inactive.map((c) => c.project)).toEqual(['b', 'f', 'g']);
    expect(board.inactive.at(-1)!.days).toBeNull();
  });

  it('shows head, time in state and the next planned milestone (overdue marked)', () => {
    const c = board.me.find((x) => x.project === 'c')!;
    expect(c.head).toBe('c.1');
    expect(c.days).toBe(275); // 2025-04-01 → 2026-01-01
    expect([c.next, c.nextOverdue]).toEqual(['c.2', true]);
    const g = board.inactive.find((x) => x.project === 'g')!;
    expect([g.head, g.next, g.nextOverdue]).toEqual([null, 'g.1', false]);
  });

  it('respects filters', () => {
    const only = statusBoard(ws, TODAY, (p) => p === 'a');
    expect([only.me.length, only.others.length, only.inactive.length]).toEqual([0, 1, 0]);
  });

  it('formats durations', () => {
    expect([formatDays(0), formatDays(1), formatDays(9), formatDays(21), formatDays(275), formatDays(800)]).toEqual([
      'today', '1 day', '9 days', '3 weeks', '9 months', '2.2 years',
    ]);
  });
});

describe('hover highlighting', () => {
  it('milestones: ancestors and descendants over order, forks, merges and directed references', () => {
    const s = relatedMilestones(ws, 'b.1');
    // ancestors: a.1 (fork origin); descendants: b.2, c.*, d.2 (merges b.2)
    for (const id of ['b.1', 'a.1', 'b.2', 'c.1', 'c.2', 'c.3', 'd.2']) expect(s.has(id)).toBe(true);
    // not related: a.2 (sibling line), d.1 (before the merge), e.1 (builds on a.2), f.1
    for (const id of ['a.2', 'd.1', 'e.1', 'f.1']) expect(s.has(id)).toBe(false);
  });

  it('milestones: directed references count, undirected partners only for the hovered one', () => {
    expect(relatedMilestones(ws, 'e.1').has('a.2')).toBe(true); // e.1 builds on a.2
    expect(relatedMilestones(ws, 'a.2').has('e.1')).toBe(true); // descendant
    expect(relatedMilestones(ws, 'a.1').has('f.1')).toBe(true); // companion partner
    expect(relatedMilestones(ws, 'b.1').has('f.1')).toBe(false); // partner of an ancestor: no
  });

  it('projects: aggregated graph', () => {
    expect([...relatedProjects(ws, 'b')].sort()).toEqual(['a', 'b', 'c', 'd']);
    expect([...relatedProjects(ws, 'a')].sort()).toEqual(['a', 'b', 'c', 'd', 'e', 'f']);
    expect([...relatedProjects(ws, 'g')]).toEqual(['g']);
  });
});

describe('dependencies view', () => {
  it('aggregates forks, merges and references to project level', () => {
    const e = projectEdges(idx).map((x) => `${x.kind}:${x.from}>${x.to}${x.arrow ? '→' : ''}`).sort();
    expect(e).toEqual(['fork:a>b', 'fork:b>c', 'merge:b>d', 'reference:e>a→', 'reference:f>a']);
  });

  it('counts several references of one type between the same projects as one edge', () => {
    const ws2 = structuredClone(ws);
    ws2.references.push({ id: 'r3', type: 'builds-on', from: 'e.1', to: 'a.1', color: null, text: '', text_align: 'center', text_position: 'above', text_orientation: 'horizontal', text_size: 10, description: '' });
    const refs = projectEdges(indexWorkspace(ws2)).filter((x) => x.kind === 'reference' && x.from === 'e');
    expect(refs.map((r) => r.count)).toEqual([2]);
  });

  it('uses the reference type colour for aggregated references', () => {
    const ws2 = structuredClone(ws);
    ws2.references[0].color = '#ff0000'; // per-reference colour is not used when aggregated
    ws2.reftypes[0].color = '#00ff00';
    const r = projectEdges(indexWorkspace(ws2)).find((x) => x.kind === 'reference' && x.arrow)!;
    expect(r.color).toBe('#00ff00');
  });

  it('drops edges to hidden projects', () => {
    const e = projectEdges(idx, (p) => p !== 'b');
    expect(e.some((x) => x.from === 'b' || x.to === 'b')).toBe(false);
  });

  it('lays out bottom-to-top: earlier work below later work', () => {
    const L = layoutDeps(idx);
    const y = (id: string) => L.nodes.find((n) => n.id === id)!.y;
    expect(y('a')).toBeGreaterThan(y('b')); // a is forked into b
    expect(y('b')).toBeGreaterThan(y('c'));
    expect(y('b')).toBeGreaterThan(y('d')); // b merged into d
    expect(y('a')).toBeGreaterThan(y('e')); // e builds on a
  });

  it('draws a directed reference from `from` to `to`, arrow end at the built-on project', () => {
    const L = layoutDeps(idx);
    const r = L.edges.find((x) => x.kind === 'reference' && x.arrow)!;
    const a = L.nodes.find((n) => n.id === 'a')!;
    const last = r.points.at(-1)!;
    expect(Math.abs(last.y - a.y)).toBeLessThanOrEqual(a.height / 2 + 0.5); // ends at a's box edge
  });
});
