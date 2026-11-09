// Status board: one card per project, in three columns by who the current state waits on.
import type { Workspace } from '../api/client';
import { isInactive } from './filters';
import { timeMs as dayMs } from './model';

export type Column = 'me' | 'others' | 'inactive';

export interface Card {
  project: string;
  group: string;
  state: string | null;
  /** days since the head milestone (time in state); null without a head */
  days: number | null;
  head: string | null;
  /** first planned milestone after the head */
  next: string | null;
  nextOverdue: boolean;
}

export function statusBoard(ws: Workspace, today: string, visible: (pid: string) => boolean = () => true): Record<Column, Card[]> {
  const ms = new Map(ws.milestones.map((m) => [m.id, m]));
  const waiting = new Map(ws.states.map((s) => [s.id, s.waiting_on]));
  const cols: Record<Column, Card[]> = { me: [], others: [], inactive: [] };
  for (const p of ws.projects) {
    if (!visible(p.id)) continue;
    const d = ws.derived.projects[p.id];
    const head = d?.head ? ms.get(d.head) : undefined;
    const after = d ? d.milestones.slice(head ? d.milestones.indexOf(head.id) + 1 : 0) : [];
    const next = after.map((id) => ms.get(id)!).find((m) => m.planned);
    const card: Card = {
      project: p.id,
      group: p.group,
      state: d?.current_state ?? null,
      days: head ? Math.round((dayMs(today) - dayMs(head.at.slice(0, 10))) / 86_400_000) : null,
      head: head?.id ?? null,
      next: next?.id ?? null,
      nextOverdue: !!next && next.at.slice(0, 10) < today,
    };
    const col: Column = isInactive(ws, p.id) ? 'inactive' : waiting.get(card.state!) === 'me' ? 'me' : 'others';
    cols[col].push(card);
  }
  // Longest in state first; projects without a head last.
  for (const c of Object.values(cols)) c.sort((a, b) => (b.days ?? -Infinity) - (a.days ?? -Infinity));
  return cols;
}

/** "today", "5 days", "3 weeks", "4 months", "1.5 years". */
export function formatDays(days: number): string {
  if (days <= 0) return days === 0 ? 'today' : 'in the future';
  if (days < 14) return `${days} day${days === 1 ? '' : 's'}`;
  if (days < 60) return `${Math.round(days / 7)} weeks`;
  if (days < 730) return `${Math.round(days / 30.44)} months`;
  return `${(days / 365.25).toFixed(1)} years`;
}
