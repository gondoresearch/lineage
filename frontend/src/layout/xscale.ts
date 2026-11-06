// Horizontal scales. Both map (date, rank) to a base x in [0, width]; the
// zoom transform {k, x} is applied on top: screenX = k * baseX + x.
// `rank` separates same-day milestones of one project (0, 1, 2…).
import { scaleUtc } from 'd3-scale';
import { dayMs } from './model';

export type Mode = 'time' | 'event';

export interface ZoomT {
  k: number;
  x: number;
}

export const IDENTITY: ZoomT = { k: 1, x: 0 };
/** Screen-pixel nudge between same-day milestones in time mode. */
export const NUDGE = 14;

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
}

const apply = (t: ZoomT, v: number) => t.k * v + t.x;
const DAY = 86_400_000;

export function timeScale(dates: string[], today: string, width: number): XScale {
  const ms = [...dates, today].map(dayMs);
  let lo = Math.min(...ms);
  let hi = Math.max(...ms);
  if (hi - lo < 30 * DAY) {
    lo -= 15 * DAY;
    hi += 15 * DAY;
  }
  const pad = (hi - lo) * 0.04;
  const scale = scaleUtc().domain([lo - pad, hi + pad]).range([0, width]);
  return {
    mode: 'time',
    x: (date, rank, t) => apply(t, scale(dayMs(date))) + rank * NUDGE,
    today: (t) => apply(t, scale(dayMs(today))),
    ticks(t, w) {
      const r = scale.copy().domain([0, width].map((v) => scale.invert((v - t.x) / t.k)));
      return r.ticks(Math.max(2, Math.floor(w / 90))).map((d) => ({ x: r(d), label: r.tickFormat()(d) }));
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
