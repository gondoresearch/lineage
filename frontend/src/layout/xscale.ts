// Horizontal scales. Both map (date, rank) to a base x in [0, width]; the
// zoom transform {k, x} is applied on top: screenX = k * baseX + x.
// `rank` orders the milestones of one day (0, 1, 2…; see ranks() in timeline.ts).
import { scaleUtc } from 'd3-scale';
import { timeMs as dayMs } from './model';

export type Mode = 'time' | 'event';

export interface ZoomT {
  k: number;
  x: number;
}

export const IDENTITY: ZoomT = { k: 1, x: 0 };
/** Screen pixels between consecutive same-day milestones in time mode (wider than a symbol),
 * when the axis has room for it. */
export const NUDGE = 22;

/** A milestone's place on the axis: its date and its rank within that day. */
export interface Slot {
  date: string;
  rank: number;
}

export interface Tick {
  x: number;
  label: string;
}

export interface XScale {
  mode: Mode;
  /** screen x of a milestone */
  x(date: string, rank: number, t: ZoomT): number;
  /** screen x of today */
  today(t: ZoomT): number;
  ticks(t: ZoomT, width: number): Tick[];
  /** how far zooming in still shows something new: until one day (in Days) or one hour (in
   * Hours) is half the width */
  maxZoom: number;
}

const apply = (t: ZoomT, v: number) => t.k * v + t.x;
const DAY = 86_400_000;

/**
 * Real time, except that nothing overlaps: the milestones of one day are NUDGE apart in
 * rank order, and a day (or today) that would land closer than NUDGE after the previous
 * day's last milestone is pushed right just enough. Zooming in restores exact dates.
 */
export function timeScale(slots: Slot[], today: string, width: number, unit: 'day' | 'hour' = 'day'): XScale {
  const ms = [...slots.map((s) => s.date), today].map(dayMs);
  let lo = Math.min(...ms);
  let hi = Math.max(...ms);
  if (hi - lo < 30 * DAY) {
    lo -= 15 * DAY;
    hi += 15 * DAY;
  }
  const pad = (hi - lo) * 0.04;
  const scale = scaleUtc().domain([lo - pad, hi + pad]).range([0, width]);
  const lastRank = new Map<string, number>();
  for (const s of slots) lastRank.set(s.date, Math.max(lastRank.get(s.date) ?? 0, s.rank));
  const days = [...new Set([...lastRank.keys(), today])].sort();

  // For one zoom transform (recomputed when it changes): each day's exact screen x (`n`)
  // and the screen x of its first slot (`s`) once crowded days are moved apart.
  let cachedFor: ZoomT | null = null;
  let layout = { start: new Map<string, number>(), n: [] as number[], s: [] as number[], e: [] as number[], gap: NUDGE };
  const placed = (t: ZoomT) => {
    if (cachedFor?.k === t.k && cachedFor.x === t.x) return layout;
    const begin = apply(t, 0) + NUDGE / 2;
    const end = apply(t, width) - NUDGE / 2;
    // The spacing: NUDGE, unless the whole axis cannot hold every day and slot that far apart
    // (a narrow window, or zoomed out); then as much as fits, so nothing leaves the axis.
    const slots = days.reduce((sum, d) => sum + (lastRank.get(d) ?? 0), 0) + days.length - 1;
    const gap = Math.min(NUDGE, (end - begin) / Math.max(1, slots));
    const span = (d: string) => (lastRank.get(d) ?? 0) * gap;
    const n = days.map((d) => apply(t, scale(dayMs(d))));
    // Forward: each day starts at its date (not before the start of the axis), or a gap
    // after the previous day's last slot.
    const s = [...n];
    if (s.length) s[0] = Math.max(s[0], begin);
    for (let i = 1; i < days.length; i++) s[i] = Math.max(s[i], s[i - 1] + span(days[i - 1]) + gap);
    // Backward: what was pushed past the end of the axis packs back to the left instead.
    let limit = end;
    for (let i = days.length - 1; i >= 0; i--) {
      s[i] = Math.min(s[i], limit - span(days[i]));
      limit = s[i] - gap;
    }
    const e = days.map((d, i) => s[i] + span(d)); // each day's last slot
    layout = { start: new Map(days.map((d, i) => [d, s[i]])), n, s, e, gap };
    cachedFor = { ...t };
    return layout;
  };
  /** Where an exact screen x ends up: a day's own moment at its first slot; a moment between
   * two days proportionally between the first one's last slot and the next one's first. */
  const warp = (t: ZoomT, x: number) => {
    const { n, s, e } = placed(t);
    if (!n.length) return x;
    if (x <= n[0]) return x + s[0] - n[0];
    for (let i = 0; i < n.length - 1; i++) {
      if (x === n[i]) return s[i];
      if (x < n[i + 1]) return e[i] + ((x - n[i]) / (n[i + 1] - n[i] || 1)) * (s[i + 1] - e[i]);
    }
    const last = n.length - 1;
    return x === n[last] ? s[last] : x + e[last] - n[last];
  };

  const dayWidth = scale(dayMs('2000-01-02')) - scale(dayMs('2000-01-01')); // px per day at zoom 1
  return {
    mode: 'time',
    maxZoom: Math.max(1, width / 2 / Math.max(unit === 'day' ? dayWidth : dayWidth / 24, 1e-9)),
    x: (date, rank, t) => {
      const l = placed(t);
      return (l.start.get(date) ?? warp(t, apply(t, scale(dayMs(date))))) + rank * l.gap;
    },
    today: (t) => placed(t).start.get(today)!,
    ticks(t, w) {
      // Ticks follow the same moves as the milestones, so a label sits where its dates are drawn;
      // labels squeezed together by crowded days are dropped.
      // Where crowded days are stretched, finer ticks (4× to 256× as many) fill the room.
      const r = scale.copy().domain([0, width].map((v) => scale.invert((v - t.x) / t.k)));
      const format = r.tickFormat();
      const base = Math.max(2, Math.floor(w / 90));
      const out: Tick[] = [];
      for (const mult of [1, 4, 16, 64, 256]) {
        for (const d of r.ticks(base * mult)) {
          if (unit === 'day' && (d.getUTCHours() || d.getUTCMinutes())) continue; // days: no times of day
          if (d.getUTCSeconds() || d.getUTCMilliseconds()) continue; // times are to the minute
          const x = warp(t, r(d));
          if (x < -60 || x > w + 60 || out.some((o) => Math.abs(o.x - x) < 60)) continue;
          out.push({ x, label: format(d) });
        }
      }
      return out.sort((a, b) => a.x - b.x);
    },
  };
}

/** Each distinct (date, rank) slot gets equal spacing. */
export function eventScale(items: { date: string; rank: number }[], today: string, width: number): XScale {
  const keys = [...new Set(items.map((i) => `${i.date}#${i.rank}`))].sort((a, b) => {
    const [da, ra] = a.split('#');
    const [db, rb] = b.split('#');
    return da < db ? -1 : da > db ? 1 : Number(ra) - Number(rb);
  });
  const step = width / Math.max(1, keys.length);
  const slot = new Map(keys.map((k, i) => [k, (i + 0.5) * step]));
  const dates = [...new Set(items.map((i) => i.date))].sort();
  const first = (d: string) => slot.get(`${d}#0`)!;
  const last = (d: string) => {
    let r = 0;
    while (slot.has(`${d}#${r + 1}`)) r++;
    return slot.get(`${d}#${r}`)!;
  };

  // Today: interpolated by real time between the neighbouring dates.
  let todayBase: number;
  const t0 = dayMs(today);
  if (!dates.length) todayBase = width / 2;
  else if (today < dates[0]) todayBase = first(dates[0]) - step / 2;
  else if (today > dates[dates.length - 1]) todayBase = last(dates[dates.length - 1]) + step / 2;
  else {
    let i = 0;
    while (dates[i + 1] !== undefined && dates[i + 1] <= today) i++;
    const d0 = dates[i];
    const d1 = dates[i + 1];
    if (d0 === today || d1 === undefined) todayBase = first(d0);
    else {
      const f = (t0 - dayMs(d0)) / (dayMs(d1) - dayMs(d0));
      todayBase = last(d0) + (first(d1) - last(d0)) * f;
    }
  }

  return {
    mode: 'event',
    maxZoom: Math.max(1, width / 2 / step),
    x: (date, rank, t) => apply(t, slot.get(`${date}#${rank}`) ?? 0),
    today: (t) => apply(t, todayBase),
    ticks(t) {
      const out: Tick[] = [];
      let prev = -Infinity;
      for (const d of dates) {
        const x = apply(t, first(d));
        if (x - prev >= 80) {
          out.push({ x, label: d });
          prev = x;
        }
      }
      return out;
    },
  };
}
