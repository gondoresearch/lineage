import { describe, expect, it } from 'vitest';
import { colors, firstColor, MARKER_NEUTRAL, NEUTRAL } from './colors';
import { makeWs } from './fixture';
import { indexWorkspace } from './model';

const base = () =>
  makeWs({
    groups: [{ id: 'g', color: '#000001' }],
    projects: [{ id: 'a', group: 'g' }, { id: 'b', group: 'g', from: 'a.1' }],
    milestones: [
      { id: 'a.1', date: '2025-01-01' },
      { id: 'b.1', date: '2025-02-01', merges: [] },
    ],
    references: [{ id: 'r', type: 'builds-on', from: 'b.1', to: 'a.1', color: null, description: '' }],
  });

describe('firstColor', () => {
  it('skips null and undefined', () => {
    expect(firstColor(null, undefined, '#123456', '#654321')).toBe('#123456');
    expect(firstColor(null)).toBeNull();
  });
});

describe('colour chains', () => {
  it('milestone: milestone → kind → project → group', () => {
    const ws = base();
    const m = ws.milestones[0];
    const c = () => colors(indexWorkspace(ws)).milestone(m);
    expect(c()).toBe('#000001');
    ws.projects[0].color = '#000002';
    expect(c()).toBe('#000002');
    ws.kinds[0].color = '#000003';
    expect(c()).toBe('#000003');
    m.color = '#000004';
    expect(c()).toBe('#000004');
  });

  it('segment: state of earlier milestone → project → group', () => {
    const ws = base();
    const m = ws.milestones[0];
    const c = () => colors(indexWorkspace(ws)).segment(m);
    expect(c()).toBe('#000001');
    ws.projects[0].color = '#000002';
    expect(c()).toBe('#000002');
    ws.kinds[0].color = '#00000f'; // kind is not in the segment chain
    m.color = '#00000e'; // nor the milestone itself
    expect(c()).toBe('#000002');
    ws.states.find((s) => s.id === 'drafting')!.color = '#000003';
    expect(c()).toBe('#000003');
    m.line_color = '#000009'; // the line's own colour wins
    expect(c()).toBe('#000009');
  });

  it('fork: fork_color → forked project → group', () => {
    const ws = base();
    const forked = ws.projects[1];
    const c = () => colors(indexWorkspace(ws)).fork(forked);
    expect(c()).toBe('#000001');
    ws.projects[0].color = '#00000f'; // origin project is not in the chain
    expect(c()).toBe('#000001');
    forked.color = '#000002';
    expect(c()).toBe('#000002');
    ws.settings.fork_color = '#000003';
    expect(c()).toBe('#000003');
  });

  it('merge: merge_color → source project → group', () => {
    const ws = base();
    const src = ws.milestones[0];
    const c = () => colors(indexWorkspace(ws)).merge(src);
    expect(c()).toBe('#000001');
    ws.projects[0].color = '#000002';
    expect(c()).toBe('#000002');
    ws.settings.merge_color = '#000003';
    expect(c()).toBe('#000003');
  });

  it('reference: reference → type → neutral gray', () => {
    const ws = base();
    const r = ws.references[0];
    const c = () => colors(indexWorkspace(ws)).reference(r);
    expect(c()).toBe(NEUTRAL);
    ws.reftypes[0].color = '#000002';
    expect(c()).toBe('#000002');
    r.color = '#000003';
    expect(c()).toBe('#000003');
    expect(colors(indexWorkspace(ws)).reftype('builds-on')).toBe('#000002');
  });

  it('project node: project → group', () => {
    const ws = base();
    const c = () => colors(indexWorkspace(ws)).project(ws.projects[0]);
    expect(c()).toBe('#000001');
    ws.projects[0].color = '#000002';
    expect(c()).toBe('#000002');
  });

  it('marker: marker → dark neutral gray', () => {
    const c = colors(indexWorkspace(base()));
    expect(c.marker({ id: 'm', name: 'm', icon: 'flag', color: null, description: '' })).toBe(MARKER_NEUTRAL);
    expect(c.marker({ id: 'm', name: 'm', icon: 'flag', color: '#000005', description: '' })).toBe('#000005');
  });
});
