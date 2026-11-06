// Shared UI state (Svelte runes). Survives view switches.
import { api, ApiError, fetchWorkspace, messagesOf, type EntityType, type Workspace } from './api/client';
import type { Filters } from './layout/filters';
import type { Mode, ZoomT } from './layout/xscale';
import { findEntity } from './lib/entities';

export const VIEWS = ['timeline', 'status', 'deps', 'settings'] as const;
export type View = (typeof VIEWS)[number];

/** What the side panel shows. */
export type Panel =
  /** `via`: the milestone whose lane line was clicked to open this state */
  | { kind: 'view'; type: EntityType; id: string; via?: string }
  | { kind: 'form'; type: EntityType; id?: string; preset?: Record<string, unknown>; title?: string }
  | { kind: 'description'; type: EntityType; id: string }
  | { kind: 'delete'; type: EntityType; id: string };

/** A form waiting for the user to click a milestone on the timeline. */
export interface Picking {
  prompt: string;
  /** milestone that cannot be picked (e.g. the reference's own source) */
  exclude?: string;
  onPick: (milestoneId: string) => void;
}

export interface Toast {
  seq: number;
  message: string;
  undo: boolean;
}

export const app = $state({
  ws: null as Workspace | null,
  error: null as string | null,
  view: 'timeline' as View,
  timeline: { mode: 'time' as Mode, zoom: { k: 1, x: 0 } as ZoomT },
  panel: null as Panel | null,
  toast: null as Toast | null,
  picking: null as Picking | null,
  /** shared by the timeline, status board and dependencies view */
  filters: { groups: [], states: [], hideInactive: false } as Filters,
  /** what the pointer is over, for hover highlighting */
  hover: null as { type: 'milestones' | 'projects'; id: string } | null,
});

/** Re-fetch every 5 s (If-None-Match, so unchanged data costs a 304) to pick up hand edits. */
export function startPolling(intervalMs = 5000): () => void {
  const timer = setInterval(() => {
    if (document.visibilityState === 'visible') load();
  }, intervalMs);
  return () => clearInterval(timer);
}

/** Ask the user to click a milestone on the timeline (switches to the timeline if needed). */
export function startPicking(p: Picking): void {
  app.picking = p;
  if (app.view !== 'timeline') location.hash = '#/timeline';
}

export function stopPicking(): void {
  app.picking = null;
}

export async function load(): Promise<void> {
  try {
    const ws = await fetchWorkspace();
    if (ws) {
      app.ws = ws;
      // Close the panel if what it shows no longer exists (e.g. after undo).
      const p = app.panel;
      if (p && 'id' in p && p.id && !findEntity(ws, p.type, p.id)) app.panel = null;
    }
    app.error = null;
  } catch (e) {
    app.error = e instanceof ApiError ? e.message : `Cannot reach the server (${e})`;
  }
}

export function routeFromHash(): void {
  const v = location.hash.replace(/^#\/?/, '') as View;
  app.view = VIEWS.includes(v) ? v : 'timeline';
}

// ------------------------------------------------------------------ panel

export function select(type: EntityType, id: string): void {
  app.panel = { kind: 'view', type, id };
}

/** Open the state of a lane line, remembering the milestone the line follows. */
export function selectStateLine(stateId: string, milestoneId: string): void {
  app.panel = { kind: 'view', type: 'states', id: stateId, via: milestoneId };
}

export function openForm(type: EntityType, opts: { id?: string; preset?: Record<string, unknown>; title?: string } = {}): void {
  app.panel = { kind: 'form', type, ...opts };
}

export function closePanel(): void {
  app.panel = null;
}

/**
 * Whether a lane line (the line after milestone `from`, in state `stateId`) is
 * the one being worked on: only the clicked line when a line was clicked, every
 * line of the state when the state itself was opened (e.g. from Settings).
 */
export function isSelectedLine(stateId: string, from: string): boolean {
  const p = app.panel;
  if (!p || p.kind !== 'view' || p.type !== 'states' || p.id !== stateId) return false;
  return p.via ? p.via === from : true;
}

/**
 * Whether the side panel is working on this entity: viewing it, editing it, its
 * description or its deletion. For milestones also the source of a fork, merge or
 * reference being created, and the milestone whose state line was clicked.
 */
export function isSelected(type: EntityType, id: string): boolean {
  const p = app.panel;
  if (!p) return false;
  if (p.type === type && 'id' in p && p.id === id) return true;
  if (type !== 'milestones') return false;
  if (p.kind === 'view') return p.via === id;
  if (p.kind === 'form' && !p.id) {
    const pre = (p.preset ?? {}) as { from?: string; merges?: string[] };
    return pre.from === id || (pre.merges ?? []).includes(id);
  }
  return false;
}

// ------------------------------------------------------------------ changes

let toastSeq = 0;
let toastTimer: ReturnType<typeof setTimeout> | undefined;

export function showToast(message: string, undo = true): void {
  app.toast = { seq: ++toastSeq, message, undo };
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { app.toast = null; }, 7000);
}

/** Run a write, reload the workspace and show a toast. Errors propagate to the caller (forms show them). */
export async function change<T>(fn: () => Promise<T>, message: string): Promise<T> {
  const result = await fn();
  await load();
  showToast(message);
  return result;
}

export async function undoLast(): Promise<void> {
  try {
    await api.undo();
    await load();
    showToast('Undone.');
  } catch (e) {
    showToast(messagesOf(e).join(' '), false);
  }
}
