import { describe, expect, it } from 'vitest';
import { legendMatcher, noHidden, showAll, showOnly, toggleHidden, visibility } from './legend';
import { makeWs } from './fixture';

const ws = makeWs({
  groups: [{ id: 'g1' }, { id: 'g2' }],
  projects: [{ id: 'a', group: 'g1' }, { id: 'b', group: 'g2' }],
  kinds: [{ id: 'draft' }, { id: 'release' }],
  milestones: [
    { id: 'a.1', date: '2026-01-01', kind: 'draft', state: 'drafting' },
    { id: 'a.2', date: '2026-01-02', kind: 'release', state: 'review' },
    { id: 'b.1', date: '2026-01-03', kind: 'draft', state: 'review' },
  ],
});

describe('legend hiding', () => {
  it('toggles, shows only one and shows all', () => {
    const h = noHidden();
    toggleHidden(h, { cat: 'kind', id: 'draft' });
    expect(h.kind).toEqual(['draft']);
    toggleHidden(h, { cat: 'kind', id: 'draft' });
    expect(h.kind).toEqual([]);
    showOnly(ws, h, { cat: 'kind', id: 'draft' });
    expect(h.kind).toEqual(['release']);
    showAll(h, 'kind');
    expect(h.kind).toEqual([]);
  });

  it('hides marks by their own type only', () => {
    const h = noHidden();
    h.kind = ['release'];
    h.state = ['drafting'];
    h.group = ['g2'];
    const v = visibility(ws, h);
    expect(v.milestone('a.2')).toBe(false);
    expect(v.milestone('a.1')).toBe(true);
    expect(v.segment('a.1')).toBe(false);
    expect(v.segment('a.2')).toBe(true);
    expect(v.projectVisible('b')).toBe(false);
    expect(v.projectVisible('a')).toBe(true);
  });
});

describe('legend hover', () => {
  it('matches marks of the hovered entry', () => {
    const m = legendMatcher(ws, { cat: 'kind', id: 'draft' });
    expect(m.milestone('a.1')).toBe(true);
    expect(m.milestone('a.2')).toBe(false);
    expect(m.project('a')).toBe(true);
    const g = legendMatcher(ws, { cat: 'group', id: 'g2' });
    expect(g.project('a')).toBe(false);
    expect(g.milestone('b.1')).toBe(true);
    expect(legendMatcher(ws, null).milestone('a.1')).toBe(true);
  });
});

describe('built-in markers', () => {
  it('hide planned milestones and their faded lines, the overdue dot and the today line', () => {
    const w = makeWs({ projects: [{ id: 'a', group: 'g' }], milestones: [{ id: 'a.1', date: '2026-01-01' }, { id: 'a.2', date: '2026-01-02', planned: true }] });
    const h = noHidden();
    h.marker = ['@planned', '@overdue', '@today'];
    const v = visibility(w, h);
    expect(v.milestone('a.2')).toBe(false);
    expect(v.milestone('a.1')).toBe(true);
    expect(v.segment('a.1', true)).toBe(false);
    expect(v.segment('a.1', false)).toBe(true);
    expect(v.overdue).toBe(false);
    expect(v.today).toBe(false);
    expect(legendMatcher(w, { cat: 'marker', id: '@planned' }).milestone('a.2')).toBe(true);
    expect(legendMatcher(w, { cat: 'marker', id: '@overdue' }, new Set(['a.2'])).milestone('a.1')).toBe(false);
  });
});
