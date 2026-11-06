// SVG stroke styles shared by the timeline, dependencies view, legend and forms.
import type { Schemas } from '../api/client';

export type Line = Schemas['State']['line'];

/** Every line pattern, in the order offered in forms. */
export const LINES: { value: Line; label: string }[] = [
  { value: 'solid', label: 'solid' },
  { value: 'dashed', label: 'dashed' },
  { value: 'long-dash', label: 'long dash' },
  { value: 'dotted', label: 'dotted' },
  { value: 'dash-dot', label: 'dash-dot' },
  { value: 'dash-dot-dot', label: 'dash-dot-dot' },
];

export const DASH: Record<string, string | undefined> = {
  solid: undefined,
  dashed: '6 4',
  'long-dash': '13 6',
  dotted: '1.5 3.5',
  'dash-dot': '8 3 2 3',
  'dash-dot-dot': '8 3 2 3 2 3',
};

export const CAP: Record<string, 'round' | 'butt'> = {
  solid: 'butt',
  dashed: 'butt',
  'long-dash': 'butt',
  dotted: 'round',
  'dash-dot': 'butt',
  'dash-dot-dot': 'butt',
};

/** Opacity multiplier for planned (future) parts of the timeline. */
export const FADED_OPACITY = 0.35;
