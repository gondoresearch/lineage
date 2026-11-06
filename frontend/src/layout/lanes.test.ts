import { describe, expect, it } from 'vitest';
import { makeWs } from './fixture';
import { dropSlots, GROUP_GAP, LANE_H, laneSubtree, layoutLanes, moveRequest, nearestSlot, type MovableProject } from './lanes';
import { indexWorkspace } from './model';

const ws = makeWs({
  groups: [{ id: 'g1' }, { id: 'g2' }],
  projects: [
    { id: 'late', group: 'g1' },
    { id: 'root', group: 'g1' },
    { id: 'fork2', group: 'g1', from: 'root.1' }, // listed before its sibling, though forked later
    { id: 'fork1', group: 'g1', from: 'root.1' },
    { id: 'deep', group: 'g1', from: 'fork1.1' }, // depth 2
    { id: 'cross', group: 'g2', from: 'root.1' }, // forked across groups
    { id: 'other', group: 'g2' },
  ],
  milestones: [
    { id: 'late.1', date: '2025-06-01' },
    { id: 'root.1', date: '2025-01-01' },
    { id: 'fork2.1', date: '2025-04-01' },
    { id: 'fork1.1', date: '2025-02-01' },
    { id: 'deep.1', date: '2025-03-01' },
    { id: 'cross.1', date: '2025-05-01' },
    { id: 'other.1', date: '2025-01-15' },
  ],
});

describe('layoutLanes', () => {
  const L = layoutLanes(indexWorkspace(ws));

  it('orders depth-first over the fork tree; roots and siblings follow the list order', () => {
    expect(L.lanes.map((l) => l.project)).toEqual(['late', 'root', 'fork2', 'fork1', 'deep', 'cross', 'other']);
    expect(L.lanes.map((l) => l.depth)).toEqual([0, 0, 1, 1, 2, 0, 0]);
  });

  it('treats a fork from another group as a root of its own group', () => {
    const cross = L.lanes.find((l) => l.project === 'cross')!;
    expect(cross.group).toBe('g2');
    expect(cross.depth).toBe(0);
  });

  it('puts a gap between groups', () => {
    expect(L.bands).toEqual([
      { group: 'g1', y0: 0, y1: 5 * LANE_H },
      { group: 'g2', y0: 5 * LANE_H + GROUP_GAP, y1: 7 * LANE_H + GROUP_GAP },
    ]);
    const y = L.lanes.map((l) => l.y);
    expect(y[1] - y[0]).toBe(LANE_H);
    expect(y[5] - y[4]).toBe(LANE_H + GROUP_GAP);
    expect(L.height).toBe(7 * LANE_H + GROUP_GAP);
  });

  it('follows group order in the file', () => {
    const swapped = { ...ws, groups: [ws.groups[1], ws.groups[0]] };
    const S = layoutLanes(indexWorkspace(swapped));
    expect(S.lanes[0].group).toBe('g2');
  });

  it('skips hidden projects; a fork whose origin is hidden becomes a root', () => {
    const S = layoutLanes(indexWorkspace(ws), (p) => p !== 'root');
    expect(S.lanes.map((l) => l.project)).toEqual(['late', 'fork2', 'fork1', 'deep', 'cross', 'other']);
    expect(S.lanes.map((l) => l.depth)).toEqual([0, 0, 0, 1, 0, 0]);
  });

  it('omits empty groups without adding a gap', () => {
    const S = layoutLanes(indexWorkspace(ws), (p) => ['other', 'cross'].includes(p));
    expect(S.bands).toEqual([{ group: 'g2', y0: 0, y1: 2 * LANE_H }]);
  });
});

describe('moving lanes', () => {
  // g1: A (with fork A1), B ; g2: C
  const mws = makeWs({
    groups: [{ id: 'g1' }, { id: 'g2' }],
    projects: [
      { id: 'A', group: 'g1' },
      { id: 'A1', group: 'g1', from: 'A.1' },
      { id: 'B', group: 'g1' },
      { id: 'C', group: 'g2' },
    ],
    milestones: [
      { id: 'A.1', date: '2025-01-01' },
      { id: 'A1.1', date: '2025-02-01' },
      { id: 'B.1', date: '2025-03-01' },
      { id: 'C.1', date: '2025-04-01' },
    ],
  });
  const M = layoutLanes(indexWorkspace(mws));
  const slots = dropSlots(M);
  const projects: MovableProject[] = mws.projects.map((p) => ({
    id: p.id,
    group: p.group,
    origin: p.from ? p.from.split('.')[0] : null,
  }));
  const slot = (group: string, before: string | null) => slots.find((s) => s.group === group && s.before === before)!;
  const apply = (pid: string, req: { group: string; position: number }) => {
    const rest = projects.filter((p) => p.id !== pid);
    rest.splice(req.position, 0, { ...projects.find((p) => p.id === pid)!, group: req.group });
    return rest.map((p) => `${p.id}:${p.group}`);
  };

  it('offers a slot before each lane and one at the end of each group', () => {
    expect(slots.map((s) => [s.group, s.before])).toEqual([
      ['g1', 'A'], ['g1', 'A1'], ['g1', 'B'], ['g1', null],
      ['g2', 'C'], ['g2', null],
    ]);
    expect(slot('g1', 'A1').y).toBe(LANE_H);
    expect(slot('g1', null).y).toBe(3 * LANE_H);
    expect(slot('g2', 'C').y).toBe(3 * LANE_H + GROUP_GAP);
  });

  it('picks the nearest slot', () => {
    expect(nearestSlot(slots, 2)).toEqual(slot('g1', 'A'));
    expect(nearestSlot(slots, 3 * LANE_H + 3)).toEqual(slot('g1', null));
    expect(nearestSlot(slots, 3 * LANE_H + GROUP_GAP - 3)).toEqual(slot('g2', 'C'));
  });

  it('moves a root above another root', () => {
    const req = moveRequest(projects, M, 'B', slot('g1', 'A'))!;
    expect(req).toEqual({ group: 'g1', position: 0 });
    expect(apply('B', req)).toEqual(['B:g1', 'A:g1', 'A1:g1', 'C:g2']);
  });

  it('moves a root with its forks: A below B', () => {
    const req = moveRequest(projects, M, 'A', slot('g1', null))!;
    expect(apply('A', req)).toEqual(['A1:g1', 'B:g1', 'A:g1', 'C:g2']);
    // laid out again, A's fork stays directly below it
    const ws2 = { ...mws, projects: ['A1', 'B', 'A', 'C'].map((id) => mws.projects.find((p) => p.id === id)!) };
    expect(layoutLanes(indexWorkspace(ws2)).lanes.map((l) => l.project)).toEqual(['B', 'A', 'A1', 'C']);
  });

  it('is a no-op when the visible order would not change', () => {
    expect(moveRequest(projects, M, 'B', slot('g1', 'B'))).toBeNull();
    expect(moveRequest(projects, M, 'B', slot('g1', null))).toBeNull();
    // a root cannot go between A and its fork: B stays after A's subtree
    expect(moveRequest(projects, M, 'B', slot('g1', 'A1'))).toBeNull();
    // dropping a project inside its own subtree changes nothing
    expect(moveRequest(projects, M, 'A', slot('g1', 'A1'))).toBeNull();
  });

  it('moves a project to another group', () => {
    const req = moveRequest(projects, M, 'B', slot('g2', 'C'))!;
    expect(req.group).toBe('g2');
    expect(apply('B', req)).toEqual(['A:g1', 'A1:g1', 'B:g2', 'C:g2']);
    const end = moveRequest(projects, M, 'C', slot('g1', null))!;
    expect(apply('C', end)).toEqual(['A:g1', 'A1:g1', 'B:g1', 'C:g1']);
  });

  it('a fork moved to another group becomes a root there', () => {
    const req = moveRequest(projects, M, 'A1', slot('g2', null))!;
    expect(apply('A1', req)).toEqual(['A:g1', 'B:g1', 'C:g2', 'A1:g2']);
  });

  it('uses the list order, not the lane order, to find the insertion point', () => {
    // fork listed before its origin (A1, A, B, C): dropping B above A must put B before A in the list
    const listed: MovableProject[] = [projects[1], projects[0], projects[2], projects[3]]; // A1, A, B, C
    const req = moveRequest(listed, M, 'B', slot('g1', 'A'))!;
    const rest = listed.filter((p) => p.id !== 'B');
    rest.splice(req.position, 0, listed[2]);
    expect(rest.map((p) => p.id).indexOf('B')).toBeLessThan(rest.map((p) => p.id).indexOf('A'));
  });

  it('finds the lane subtree that moves along to another group', () => {
    const tree: MovableProject[] = [
      { id: 'P', group: 'g1', origin: null },
      { id: 'F', group: 'g1', origin: 'P' },
      { id: 'FF', group: 'g1', origin: 'F' }, // fork of a fork
      { id: 'X', group: 'g2', origin: 'P' }, // already in another group: its own tree
      { id: 'XF', group: 'g2', origin: 'X' },
      { id: 'Q', group: 'g1', origin: null },
    ];
    expect(laneSubtree(tree, 'P').sort()).toEqual(['F', 'FF']);
    expect(laneSubtree(tree, 'F')).toEqual(['FF']);
    expect(laneSubtree(tree, 'Q')).toEqual([]);
  });
});
