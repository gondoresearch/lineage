import { describe, expect, it } from 'vitest';
import { MARKER_NEUTRAL } from './colors';
import { makeWs } from './fixture';
import { layoutLanes } from './lanes';
import { indexWorkspace } from './model';
import { computeTimeline, placeText, R, ranks, segmentText } from './timeline';
import { eventScale, IDENTITY, timeScale } from './xscale';

const TODAY = '2026-01-01';

const ws = makeWs({
  groups: [{ id: 'g' }],
  projects: [
    { id: 'a', group: 'g' },
    { id: 'b', group: 'g', from: 'a.2' },
    { id: 'c', group: 'g' },
    { id: 'd', group: 'g' },
  ],
  milestones: [
    { id: 'a.1', date: '2025-01-01', state: 'drafting' },
    { id: 'a.2', date: '2025-03-01', state: 'review' },
    { id: 'a.3', date: '2025-06-01', state: 'drafting' },
    { id: 'a.4', date: '2025-12-01', state: 'review', planned: true }, // overdue
    { id: 'a.5', date: '2026-06-01', state: 'done', planned: true }, // future
    { id: 'b.1', date: '2025-04-01', state: 'drafting' },
    { id: 'b.2', date: '2025-05-01', state: 'done' }, // merged into c, waiting on nobody
    { id: 'c.1', date: '2025-02-01', state: 'review' },
    { id: 'c.2', date: '2025-07-01', state: 'review', merges: ['b.2'] },
    { id: 'd.1', date: '2025-08-01', state: 'done' },
    { id: 'd.2', date: '2025-08-01', state: 'done' }, // same day as d.1
  ],
  references: [
    { id: 'r1', type: 'builds-on', from: 'd.1', to: 'a.3', color: null, description: '' },
    { id: 'r2', type: 'companion', from: 'a.1', to: 'a.3', color: null, description: '' },
  ],
});
const idx = indexWorkspace(ws);
const lanes = layoutLanes(idx);
const dates = ws.milestones.map((m) => m.date);

for (const [name, xs] of [
  ['time', timeScale(dates, TODAY, 1000)],
  ['event', eventScale(ws.milestones.map((m) => ({ date: m.date, rank: ranks(idx).get(m.id)! })), TODAY, 1000)],
] as const) {
  describe(`computeTimeline (${name} scale)`, () => {
    const g = computeTimeline(idx, lanes, xs, { k: 1.5, x: -20 }, TODAY);
    const node = (id: string) => g.nodes.find((n) => n.id === id)!;
    const dist = (x: number, y: number, id: string) => Math.hypot(x - node(id).x, y - node(id).y);

    it('places nodes on their lanes', () => {
      expect(node('b.1').y).toBe(lanes.y.get('b'));
      expect(node('a.1').x).toBeLessThan(node('a.2').x);
    });

    it('edge endpoints sit on the edge of their nodes', () => {
      expect(g.edges.length).toBe(4);
      for (const e of g.edges) {
        expect(dist(e.x1, e.y1, e.from)).toBeCloseTo(R, 6);
        expect(dist(e.x2, e.y2, e.to)).toBeCloseTo(R, 6);
        expect(e.path.startsWith(`M${Math.round(e.x1 * 100) / 100},${Math.round(e.y1 * 100) / 100}`)).toBe(true);
        expect(e.path.endsWith(`${Math.round(e.x2 * 100) / 100},${Math.round(e.y2 * 100) / 100}`)).toBe(true);
      }
    });

    it('fork and merge edges leave vertically and enter horizontally', () => {
      const fork = g.edges.find((e) => e.kind === 'fork')!;
      expect([fork.from, fork.to]).toEqual(['a.2', 'b.1']);
      expect(fork.x1).toBe(node('a.2').x); // leaves through the bottom
      expect(fork.y2).toBe(node('b.1').y); // enters through the side
      const merge = g.edges.find((e) => e.kind === 'merge')!;
      expect([merge.from, merge.to]).toEqual(['b.2', 'c.2']);
    });

    it('references carry their type style; only directed ones get an arrow', () => {
      const r1 = g.edges.find((e) => e.id === 'r1')!;
      const r2 = g.edges.find((e) => e.id === 'r2')!;
      expect([r1.line, r1.arrow, r1.opacity]).toEqual(['dashed', true, 1]);
      expect([r2.line, r2.arrow, r2.opacity]).toEqual(['dotted', false, 0.5]);
      expect([r1.from, r1.to]).toEqual(['d.1', 'a.3']);
    });

    it('segments stop at node edges and use the earlier state', () => {
      const s = g.segments.find((s) => s.from === 'a.1')!;
      expect(s.x1).toBeCloseTo(node('a.1').x + R, 6);
      expect(s.x2).toBeCloseTo(node('a.2').x - R, 6);
      expect([s.line, s.faded]).toEqual(['solid', false]);
      expect(g.segments.find((s) => s.from === 'a.2')!.line).toBe('dashed');
      expect(g.segments.every((s) => s.opacity === 1)).toBe(true);
      expect(g.edges.filter((e) => e.kind !== 'reference').every((e) => e.opacity === 1)).toBe(true);
    });

    it('fades segments to future planned milestones, starting at today', () => {
      const toFuture = g.segments.find((s) => s.from === 'a.4')!;
      expect(toFuture.faded).toBe(true);
      expect(toFuture.x1).toBeCloseTo(Math.max(node('a.4').x + R, g.todayX), 6);
      expect(toFuture.x2).toBeCloseTo(node('a.5').x - R, 6);
    });

    it('breaks head → today around an overdue planned milestone instead of crossing it', () => {
      const pieces = g.segments.filter((s) => s.from === 'a.3');
      expect(pieces.map((s) => s.faded)).toEqual([false, false]);
      expect(pieces[0].x1).toBeCloseTo(node('a.3').x + R, 6);
      expect(pieces[0].x2).toBeCloseTo(node('a.4').x - R, 6);
      expect(pieces[1].x1).toBeCloseTo(node('a.4').x + R, 6);
      expect(pieces[1].x2).toBe(g.todayX);
      // no segment of any lane passes through a node
      for (const s of g.segments) {
        for (const n of g.nodes.filter((n) => n.y === s.y)) {
          expect(n.x + R <= s.x1 + 1e-6 || n.x - R >= s.x2 - 1e-6).toBe(true);
        }
      }
    });

    it('fades the segment to an overdue planned milestone when nobody is waited on', () => {
      const ws2 = structuredClone(ws);
      ws2.milestones.find((m) => m.id === 'a.3')!.state = 'done';
      const idx2 = indexWorkspace(ws2);
      const g2 = computeTimeline(idx2, layoutLanes(idx2), xs, { k: 1.5, x: -20 }, TODAY);
      const s = g2.segments.filter((s) => s.from === 'a.3');
      expect(s.map((x) => x.faded)).toEqual([true]);
      expect(s[0].x2).toBeCloseTo(g2.nodes.find((n) => n.id === 'a.4')!.x - R, 6);
    });

    it('draws head → today only when waiting on someone and not merged', () => {
      const toToday = (p: string) => g.segments.filter((s) => s.project === p && !s.faded && s.x2 === g.todayX);
      expect(toToday('a').map((s) => [s.from, s.line])).toEqual([['a.3', 'solid']]);
      expect(toToday('c').map((s) => [s.from, s.line])).toEqual([['c.2', 'dashed']]);
      expect(toToday('b')).toEqual([]); // merged
      expect(toToday('d')).toEqual([]); // waiting on nobody
    });

    it('marks planned and overdue milestones', () => {
      expect([node('a.4').planned, node('a.4').overdue]).toEqual([true, true]);
      expect([node('a.5').planned, node('a.5').overdue]).toEqual([true, false]);
    });

    it('separates same-day milestones of a project', () => {
      expect(node('d.2').x).toBeGreaterThan(node('d.1').x);
    });
  });
}

describe('line opacity', () => {
  it("segments take their state's opacity", () => {
    const ws2 = structuredClone(ws);
    ws2.states.find((s) => s.id === 'review')!.opacity = 0.4;
    const idx2 = indexWorkspace(ws2);
    const g = computeTimeline(idx2, layoutLanes(idx2), timeScale(dates, TODAY, 1000), IDENTITY, TODAY);
    expect(g.segments.find((s) => s.from === 'a.2')!.opacity).toBe(0.4); // a.2 is in review
    expect(g.segments.find((s) => s.from === 'a.1')!.opacity).toBe(1);
  });
});

describe('filtered lanes', () => {
  it('drops edges to hidden projects', () => {
    const L = layoutLanes(idx, (p) => p !== 'b');
    const g = computeTimeline(idx, L, timeScale(dates, TODAY, 1000), IDENTITY, TODAY);
    expect(g.edges.filter((e) => e.kind !== 'reference')).toEqual([]);
    expect(g.nodes.some((n) => n.project === 'b')).toBe(false);
  });
});

describe('kind size and markers', () => {
  const ws3 = makeWs({
    groups: [{ id: 'g' }],
    projects: [{ id: 'a', group: 'g' }, { id: 'b', group: 'g', from: 'a.1' }],
    kinds: [
      { id: 'draft', shape: 'open-circle' },
      { id: 'big', shape: 'filled-star', size: 1.5 },
      { id: 'small', shape: 'triangle', size: 0.5 },
    ],
    milestones: [
      { id: 'a.1', date: '2025-01-01', kind: 'big', markers: ['flag', 'gone'] },
      { id: 'a.2', date: '2025-03-01', kind: 'small' },
      { id: 'b.1', date: '2025-04-01' },
    ],
    references: [{ id: 'r', type: 'builds-on', from: 'b.1', to: 'a.2', color: null, description: '' }],
    markers: [{ id: 'flag', name: 'deadline', icon: 'flag', color: null, description: '' }],
  });
  const idx3 = indexWorkspace(ws3);
  const g = computeTimeline(idx3, layoutLanes(idx3), timeScale(ws3.milestones.map((m) => m.date), TODAY, 1000), IDENTITY, TODAY);
  const node = (id: string) => g.nodes.find((n) => n.id === id)!;

  it('scales the node radius by the kind size', () => {
    expect([node('a.1').r, node('a.2').r, node('b.1').r]).toEqual([R * 1.5, R * 0.5, R]);
  });

  it('stops lines at each node’s own radius', () => {
    const s = g.segments.find((x) => x.from === 'a.1' && x.to === 'a.2')!;
    expect(s.x1).toBeCloseTo(node('a.1').x + R * 1.5, 6);
    expect(s.x2).toBeCloseTo(node('a.2').x - R * 0.5, 6);
    for (const e of g.edges) {
      const a = node(e.from);
      const b = node(e.to);
      expect(Math.hypot(e.x1 - a.x, e.y1 - a.y)).toBeCloseTo(a.r, 6);
      expect(Math.hypot(e.x2 - b.x, e.y2 - b.y)).toBeCloseTo(b.r, 6);
    }
  });

  it('resolves markers (unknown ids skipped) with the neutral marker colour', () => {
    expect(node('a.1').markers).toEqual([{ id: 'flag', icon: 'flag', color: MARKER_NEUTRAL, name: 'deadline' }]);
    expect(node('a.2').markers).toEqual([]);
  });
});

describe('line thickness and text', () => {
  const ws4 = makeWs({
    groups: [{ id: 'g' }],
    projects: [{ id: 'a', group: 'g' }, { id: 'b', group: 'g', from: 'a.1' }],
    states: [
      { id: 'drafting', line: 'solid', waiting_on: 'me', line_width: 4, text: 'writing', text_align: 'left', text_position: 'below' },
      { id: 'review', line: 'dashed', waiting_on: 'others', text: 'a very long text that cannot fit on a short segment' },
    ],
    milestones: [
      { id: 'a.1', date: '2025-01-01', state: 'drafting' },
      { id: 'a.2', date: '2025-06-01', state: 'review' },
      { id: 'a.3', date: '2025-06-20', state: 'drafting' },
      { id: 'b.1', date: '2025-02-01', state: 'review', merges: [] },
    ],
    references: [
      { id: 'r', type: 'builds-on', from: 'b.1', to: 'a.2', color: null, description: '', text: 'uses Lemma 2', text_align: 'right', text_position: 'middle' },
      { id: 'q', type: 'companion', from: 'a.1', to: 'a.3', color: null, description: '' },
    ],
    settings: { fork_color: null, merge_color: null, fork_width: 3, merge_width: 1.8 },
  });
  const idx4 = indexWorkspace(ws4);
  const g = computeTimeline(idx4, layoutLanes(idx4), timeScale(ws4.milestones.map((m) => m.date), TODAY, 1000), IDENTITY, TODAY);

  it('takes widths from the state, the reference type and the fork/merge settings', () => {
    expect(g.segments.find((s) => s.from === 'a.1')!.width).toBe(4);
    expect(g.segments.find((s) => s.from === 'a.2')!.width).toBe(2.5);
    expect(g.edges.find((e) => e.kind === 'fork')!.width).toBe(3);
    expect(g.edges.find((e) => e.id === 'r')!.width).toBe(1.4);
  });

  it('places state text along the segment, below a thick line, left aligned', () => {
    const s = g.segments.find((x) => x.from === 'a.1')!;
    expect(s.label).toEqual({ text: 'writing', x: s.x1 + 4, y: s.y + 4 / 2 + 10, anchor: 'start', baseline: 'auto', angle: 0, size: 10 });
  });

  it('hides state text that does not fit, and shows none when unset', () => {
    expect(g.segments.find((x) => x.from === 'a.2' && x.to === 'a.3')!.label).toBeNull(); // short segment, long text
    expect(segmentText('', 0, 500, 0, 2, 'center', 'above')).toBeNull();
    expect(segmentText('ok', 0, 100, 10, 2, 'center', 'above')).toEqual({ text: 'ok', x: 50, y: 10 - 1 - 3, anchor: 'middle', baseline: 'auto', angle: 0, size: 10 });
  });

  it('places reference text along the line: right = near `to`, middle = on the line', () => {
    const e = g.edges.find((x) => x.id === 'r')!;
    expect(e.label!.text).toBe('uses Lemma 2');
    expect(e.label!.baseline).toBe('central');
    expect(e.label!.x).toBeCloseTo(e.x1 + (e.x2 - e.x1) * 0.85, 6);
    expect(e.label!.y).toBeCloseTo(e.y1 + (e.y2 - e.y1) * 0.85, 6);
    expect(g.edges.find((x) => x.id === 'q')!.label).toBeNull();
  });
});

describe('reference text orientation', () => {
  const at = { x: 100, y: 100 };

  it('horizontal: level whatever the line direction', () => {
    const t = placeText('x', at, { x: 1, y: 1 }, 2, 'above', 'horizontal');
    expect([t.angle, t.x, t.y]).toEqual([0, 100, 100 - 1 - 3]);
  });

  it('along: rotated with the line, offset perpendicular to it', () => {
    const t = placeText('x', at, { x: 1, y: 1 }, 2, 'above', 'along');
    expect(t.angle).toBeCloseTo(45, 6);
    // 4px "above" a 45° line: up and to the right of the anchor point
    expect(t.x).toBeCloseTo(100 + 4 * Math.SQRT1_2, 6);
    expect(t.y).toBeCloseTo(100 - 4 * Math.SQRT1_2, 6);
    expect(placeText('x', at, { x: 1, y: 1 }, 2, 'middle', 'along')).toMatchObject({ x: 100, y: 100, baseline: 'central' });
  });

  it('along: never upside down', () => {
    expect(placeText('x', at, { x: -1, y: -1 }, 2, 'above', 'along').angle).toBeCloseTo(45, 6); // line drawn right-to-left
    expect(placeText('x', at, { x: -1, y: 1 }, 2, 'above', 'along').angle).toBeCloseTo(-45, 6);
    expect(placeText('x', at, { x: 0, y: 1 }, 2, 'above', 'along').angle).toBeCloseTo(90, 6); // vertical
  });

  it('is applied to references in the timeline', () => {
    const ws5 = makeWs({
      groups: [{ id: 'g' }],
      projects: [{ id: 'a', group: 'g' }, { id: 'b', group: 'g' }],
      milestones: [{ id: 'a.1', date: '2025-01-01' }, { id: 'b.1', date: '2025-06-01' }],
      references: [{ id: 'r', type: 'builds-on', from: 'b.1', to: 'a.1', color: null, description: '', text: 'uses', text_orientation: 'along' }],
    });
    const idx5 = indexWorkspace(ws5);
    const g = computeTimeline(idx5, layoutLanes(idx5), timeScale(['2025-01-01', '2025-06-01'], TODAY, 1000), IDENTITY, TODAY);
    const e = g.edges.find((x) => x.id === 'r')!;
    const expected = (Math.atan2(e.y2 - e.y1, e.x2 - e.x1) * 180) / Math.PI;
    const upright = expected > 90 ? expected - 180 : expected < -90 ? expected + 180 : expected;
    expect(e.label!.angle).toBeCloseTo(upright, 6);
    expect(e.label!.angle).not.toBe(0);
  });
});

describe('per-line text and text size', () => {
  const ws6 = makeWs({
    groups: [{ id: 'g' }],
    projects: [{ id: 'a', group: 'g' }],
    states: [{ id: 'drafting', line: 'solid', waiting_on: 'me', text: 'state default' }],
    milestones: [
      { id: 'a.1', date: '2025-01-01', line_text: 'only this line', line_text_size: 16, line_text_position: 'below' },
      { id: 'a.2', date: '2025-06-01' },
      { id: 'a.3', date: '2025-12-01' },
    ],
  });
  const idx6 = indexWorkspace(ws6);
  const g = computeTimeline(idx6, layoutLanes(idx6), timeScale(['2025-01-01', '2025-12-01'], TODAY, 1000), IDENTITY, TODAY);
  const label = (from: string) => g.segments.find((s) => s.from === from && s.to !== null)!.label!;

  it("a milestone's line text replaces the state's default on that line only", () => {
    expect(label('a.1').text).toBe('only this line');
    expect(label('a.2').text).toBe('state default');
  });

  it('uses the text size for placement below the line', () => {
    expect(label('a.1').size).toBe(16);
    expect(label('a.1').y).toBeCloseTo(g.segments[0].y + 2.5 / 2 + 16, 6);
    expect(label('a.2').size).toBe(10);
  });

  it('bigger text needs more room before it is shown', () => {
    expect(segmentText('abcdefghij', 0, 70, 0, 2, 'center', 'above', 10)).not.toBeNull(); // 56 + 8 <= 70
    expect(segmentText('abcdefghij', 0, 70, 0, 2, 'center', 'above', 16)).toBeNull(); // 89.6 + 8 > 70
  });
});

describe('closing kinds', () => {
  const ws7 = makeWs({
    groups: [{ id: 'g' }],
    projects: [{ id: 'a', group: 'g' }, { id: 'b', group: 'g' }],
    kinds: [{ id: 'draft', shape: 'open-circle' }, { id: 'closed', shape: 'filled-square', closes: true }],
    milestones: [
      { id: 'a.1', date: '2025-01-01' },
      { id: 'a.2', date: '2025-06-01', kind: 'closed', state: null },
      { id: 'b.1', date: '2025-01-01' },
      { id: 'b.2', date: '2025-06-01', kind: 'closed', state: null },
      { id: 'b.3', date: '2025-09-01', planned: true },
    ],
  });
  const idx7 = indexWorkspace(ws7);
  const g = computeTimeline(idx7, layoutLanes(idx7), timeScale(['2025-01-01', '2025-09-01'], TODAY, 1000), IDENTITY, TODAY);

  it('draws the line up to a closing milestone, and nothing after it', () => {
    expect(g.segments.filter((s) => s.project === 'a').map((s) => [s.from, s.to])).toEqual([['a.1', 'a.2']]);
    expect(g.segments.filter((s) => s.project === 'b').map((s) => [s.from, s.to])).toEqual([['b.1', 'b.2']]);
  });

  it('a closed project has no state and no line to today', () => {
    expect(ws7.derived.projects.a).toMatchObject({ head: 'a.2', closed: true, current_state: null });
    expect(g.segments.some((s) => s.to === null)).toBe(false);
  });
});

describe("a single line's own look", () => {
  const ws8 = makeWs({
    groups: [{ id: 'g' }],
    projects: [{ id: 'a', group: 'g' }],
    milestones: [
      { id: 'a.1', date: '2025-01-01', line_pattern: 'dash-dot', line_color: '#123456', line_width: 6, line_opacity: 0.5 },
      { id: 'a.2', date: '2025-06-01' },
      { id: 'a.3', date: '2025-12-01' },
    ],
  });
  const idx8 = indexWorkspace(ws8);
  const g = computeTimeline(idx8, layoutLanes(idx8), timeScale(['2025-01-01', '2025-12-01'], TODAY, 1000), IDENTITY, TODAY);
  const seg = (from: string) => g.segments.find((s) => s.from === from && s.to !== null)!;

  it('overrides pattern, colour, thickness and opacity of that line only', () => {
    expect([seg('a.1').line, seg('a.1').color, seg('a.1').width, seg('a.1').opacity]).toEqual(['dash-dot', '#123456', 6, 0.5]);
    expect([seg('a.2').line, seg('a.2').width, seg('a.2').opacity]).toEqual(['solid', 2.5, 1]); // the state's look
  });
});
