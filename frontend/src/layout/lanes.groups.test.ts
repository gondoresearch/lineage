import { describe, expect, it } from 'vitest';
import { makeWs } from './fixture';
import { domainMoveRequest, domainSlots, groupMoveRequest, groupSlots, layoutLanes } from './lanes';
import { indexWorkspace } from './model';

const ws = makeWs({
  domains: [{ id: 'd1', name: 'd1', color: '#000000', description: '' }, { id: 'd2', name: 'd2', color: '#000000', description: '' }],
  groups: [{ id: 'free' }, { id: 'a', domain: 'd1' }, { id: 'b', domain: 'd1' }, { id: 'c', domain: 'd2' }],
  projects: [
    { id: 'pf', group: 'free' },
    { id: 'pa', group: 'a' },
    { id: 'pb', group: 'b' },
    { id: 'pc', group: 'c' },
  ],
  milestones: ['pf', 'pa', 'pb', 'pc'].map((p) => ({ id: `${p}.1`, date: '2025-01-01' })),
});
const L = layoutLanes(indexWorkspace(ws));
const groups = ws.groups.map((g) => ({ id: g.id, domain: g.domain ?? null }));
const slot = (domain: string | null, before: string | null) => groupSlots(L).find((s) => s.domain === domain && s.before === before)!;

describe('group slots', () => {
  it('has a slot before each group and at the end of each domain block', () => {
    expect(groupSlots(L).map((s) => [s.domain, s.before])).toEqual([
      [null, 'free'], [null, null], ['d1', 'a'], ['d1', 'b'], ['d1', null], ['d2', 'c'], ['d2', null],
    ]);
    expect(slot('d1', 'a').y).toBe(L.bands.find((b) => b.group === 'a')!.y0);
  });
});

describe('groupMoveRequest', () => {
  it('reorders within a domain', () => {
    expect(groupMoveRequest(groups, 'b', slot('d1', 'a'))).toEqual({ position: 1 });
    expect(groupMoveRequest(groups, 'a', slot('d1', null))).toEqual({ position: 2 });
  });
  it('is a no-op when the order stays', () => {
    expect(groupMoveRequest(groups, 'a', slot('d1', 'b'))).toBeNull();
    expect(groupMoveRequest(groups, 'b', slot('d1', null))).toBeNull();
  });
  it('reassigns the domain', () => {
    expect(groupMoveRequest(groups, 'a', slot('d2', 'c'))).toEqual({ domain: 'd2', position: 2 });
    expect(groupMoveRequest(groups, 'c', slot('d1', null))).toEqual({ domain: 'd1', position: 3 });
    expect(groupMoveRequest(groups, 'a', slot(null, null))).toEqual({ domain: null, position: 1 });
  });
  it('moving into the same domain-less position within another domain still reassigns', () => {
    expect(groupMoveRequest(groups, 'free', slot('d2', null))).toEqual({ domain: 'd2', position: 3 });
  });
  it('keeps hidden groups in place (index in the full list)', () => {
    const hidden = layoutLanes(indexWorkspace(ws), (pid) => pid !== 'pb');
    const s = groupSlots(hidden).find((x) => x.domain === 'd2' && x.before === 'c')!;
    // 'b' is not on screen but still counted
    expect(groupMoveRequest(groups, 'a', s)).toEqual({ domain: 'd2', position: 2 });
  });
});

describe('domains', () => {
  it('has slots before each domain and after the last', () => {
    expect(domainSlots(L).map((s) => s.before)).toEqual(['d1', 'd2', null]);
  });
  it('reorders domains and ignores no-ops', () => {
    const doms = [{ id: 'd1' }, { id: 'd2' }];
    expect(domainMoveRequest(doms, ['d1', 'd2'], 'd2', { before: 'd1', y: 0 })).toEqual({ position: 0 });
    expect(domainMoveRequest(doms, ['d1', 'd2'], 'd1', { before: null, y: 0 })).toEqual({ position: 1 });
    expect(domainMoveRequest(doms, ['d1', 'd2'], 'd1', { before: 'd2', y: 0 })).toBeNull();
    expect(domainMoveRequest(doms, ['d1', 'd2'], 'd2', { before: null, y: 0 })).toBeNull();
  });
});
