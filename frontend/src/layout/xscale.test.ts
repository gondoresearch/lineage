import { describe, expect, it } from 'vitest';
import { eventScale, IDENTITY, NUDGE, timeScale } from './xscale';

describe('eventScale', () => {
  const items = [
    { date: '2025-01-01', rank: 0 },
    { date: '2025-01-01', rank: 0 }, // same slot in another project
    { date: '2025-03-01', rank: 0 },
    { date: '2025-03-01', rank: 1 }, // second milestone that day in one project
    { date: '2026-01-01', rank: 0 },
  ];
  const xs = eventScale(items, '2025-08-01', 400);

  it('gives each distinct slot equal spacing regardless of time gaps', () => {
    const a = xs.x('2025-01-01', 0, IDENTITY);
    const b = xs.x('2025-03-01', 0, IDENTITY);
    const c = xs.x('2025-03-01', 1, IDENTITY);
    const d = xs.x('2026-01-01', 0, IDENTITY);
    expect([a, b, c, d]).toEqual([50, 150, 250, 350]);
  });

  it('interpolates today between neighbouring dates by real time', () => {
    const last = xs.x('2025-03-01', 1, IDENTITY);
    const next = xs.x('2026-01-01', 0, IDENTITY);
    const today = xs.today(IDENTITY);
    expect(today).toBeGreaterThan(last);
    expect(today).toBeLessThan(next);
    // Aug 1 is 153 of 306 days from Mar 1 to Jan 1: halfway
    expect(today).toBeCloseTo((last + next) / 2, 0);
  });

  it('places today on a milestone date exactly and outside the range half a step out', () => {
    expect(eventScale(items, '2025-03-01', 400).today(IDENTITY)).toBe(150);
    expect(eventScale(items, '2027-01-01', 400).today(IDENTITY)).toBe(400);
    expect(eventScale(items, '2024-01-01', 400).today(IDENTITY)).toBe(0);
  });

  it('applies the zoom transform', () => {
    expect(xs.x('2025-01-01', 0, { k: 2, x: -10 })).toBe(90);
  });

  it('labels each distinct date, thinning crowded ones', () => {
    expect(xs.ticks(IDENTITY, 400).map((t) => t.label)).toEqual(['2025-01-01', '2025-03-01', '2026-01-01']);
    // slots at 15, 45, 105 px: the middle label is too close to the first
    expect(xs.ticks({ k: 0.3, x: 0 }, 400).map((t) => t.label)).toEqual(['2025-01-01', '2026-01-01']);
  });
});

describe('timeScale', () => {
  const xs = timeScale(['2025-01-01', '2025-12-31'], '2025-07-02', 1000);

  it('is linear in time and keeps order', () => {
    const a = xs.x('2025-01-01', 0, IDENTITY);
    const b = xs.x('2025-12-31', 0, IDENTITY);
    expect(a).toBeGreaterThan(0);
    expect(b).toBeLessThan(1000);
    expect(xs.today(IDENTITY)).toBeCloseTo((a + b) / 2, 0);
  });

  it('nudges same-day milestones apart in screen pixels', () => {
    const z = { k: 3, x: 5 };
    expect(xs.x('2025-01-01', 1, z) - xs.x('2025-01-01', 0, z)).toBe(NUDGE);
  });

  it('ticks follow the zoom', () => {
    const t = xs.ticks({ k: 4, x: -1500 }, 1000);
    expect(t.length).toBeGreaterThan(1);
    for (const tick of t) expect(tick.x).toBeGreaterThanOrEqual(0);
  });
});
