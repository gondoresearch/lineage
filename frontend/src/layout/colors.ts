// Colour resolution: each drawn element takes the first colour set along its chain.
import type { Marker, Milestone, Project, Reference } from '../api/client';
import type { Index } from './model';

export const NEUTRAL = '#9a9a9a';
/** Default colour for marker badges (darker than NEUTRAL so the small icons read well). */
export const MARKER_NEUTRAL = '#5f6368';

export function firstColor(...chain: (string | null | undefined)[]): string | null {
  for (const c of chain) if (c) return c;
  return null;
}

function projectChain(idx: Index, p: Project | undefined): (string | null | undefined)[] {
  return [p?.color, p ? idx.groups.get(p.group)?.color : null];
}

export function colors(idx: Index) {
  const s = idx.ws.settings;
  return {
    /** milestone → kind → project → group */
    milestone(m: Milestone): string {
      const p = idx.projects.get(m.project);
      return firstColor(m.color, idx.kinds.get(m.kind)?.color, ...projectChain(idx, p)) ?? NEUTRAL;
    },
    /** the line's own colour (on the earlier milestone) → its state → project → group */
    segment(earlier: Milestone): string {
      const p = idx.projects.get(earlier.project);
      const st = earlier.state ? idx.states.get(earlier.state) : undefined;
      return firstColor(earlier.line_color, st?.color, ...projectChain(idx, p)) ?? NEUTRAL;
    },
    /** fork_color → forked project → group */
    fork(forked: Project): string {
      return firstColor(s.fork_color, ...projectChain(idx, forked)) ?? NEUTRAL;
    },
    /** merge_color → source project → group */
    merge(source: Milestone): string {
      return firstColor(s.merge_color, ...projectChain(idx, idx.projects.get(source.project))) ?? NEUTRAL;
    },
    /** reference → reference type → neutral gray */
    reference(r: Reference): string {
      return firstColor(r.color, idx.reftypes.get(r.type)?.color) ?? NEUTRAL;
    },
    /** reference type → neutral gray (aggregated reference edges) */
    reftype(typeId: string): string {
      return firstColor(idx.reftypes.get(typeId)?.color) ?? NEUTRAL;
    },
    /** marker → dark neutral gray */
    marker(m: Marker): string {
      return firstColor(m.color) ?? MARKER_NEUTRAL;
    },
    /** project → group (dependencies-view node, lane label) */
    project(p: Project): string {
      return firstColor(...projectChain(idx, p)) ?? NEUTRAL;
    },
  };
}

export type Colors = ReturnType<typeof colors>;
