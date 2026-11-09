// Shared UI state (Svelte runes). Survives view switches.
import { api, ApiError, auth, fetchMe, fetchWorkspace, messagesOf, resetEtag, type EntityType, type Workspace } from './api/client';
import type { Filters } from './layout/filters';
import type { Unit } from './layout/model';
import type { Mode, ZoomT } from './layout/xscale';
import { findEntity } from './lib/entities';

export const VIEWS = ['timeline', 'status', 'deps', 'settings'] as const;
export type View = (typeof VIEWS)[number];

/** What the side panel shows. */
export type Panel =
  | { kind: 'view'; type: EntityType; id: string }
  /** one lane line: the line after milestone `id` */
  | { kind: 'line'; type: 'milestones'; id: string }
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
  /** logged-in user name; null: not logged in; undefined: not checked yet */
  user: undefined as string | null | undefined,
  /** whether the logged-in user is an admin (can manage the other accounts) */
  admin: false,
  ws: null as Workspace | null,
  /** running lineage version, from the backend */
  version: null as string | null,
  error: null as string | null,
  view: 'timeline' as View,
  timeline: { mode: 'time' as Mode, unit: 'day' as Unit, zoom: { k: 1, x: 0 } as ZoomT },
  panel: null as Panel | null,
  toast: null as Toast | null,
  picking: null as Picking | null,
  /** shared by the timeline, status board and dependencies view */
  filters: { groups: [], states: [], hideInactive: false } as Filters,
  /** what the pointer is over, for hover highlighting */
  hover: null as { type: 'milestones' | 'projects'; id: string } | null,
});

// ------------------------------------------------------------------ theme

export type Theme = 'auto' | 'light' | 'dark';
const THEME_KEY = 'lineage-theme';

/** The saved theme choice ('auto' follows the system). Storage may be unavailable. */
export function savedTheme(): Theme {
  try {
    const t = localStorage.getItem(THEME_KEY);
    return t === 'light' || t === 'dark' ? t : 'auto';
  } catch {
    return 'auto';
  }
}

export function applyTheme(t: Theme): void {
  if (t === 'auto') delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = t;
  try {
    if (t === 'auto') localStorage.removeItem(THEME_KEY);
    else localStorage.setItem(THEME_KEY, t);
  } catch {
    // private mode etc.: the choice just isn't remembered
  }
}

/** Re-fetch every 5 s (If-None-Match, so unchanged data costs a 304) to pick up hand edits. */
export function startPolling(intervalMs = 5000): () => void {
  const timer = setInterval(() => {
    if (document.visibilityState === 'visible' && app.user) load();
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
    if (e instanceof ApiError && e.status === 401) {
      loggedOut();
      return;
    }
    app.error = e instanceof ApiError ? e.message : `Cannot reach the server (${e})`;
  }
}

// ------------------------------------------------------------------ session

/** Clear everything that belongs to the previous user. */
function loggedOut(): void {
  app.user = null;
  app.admin = false;
  app.ws = null;
  app.panel = null;
  app.picking = null;
  app.toast = null;
  app.error = null;
  resetEtag();
}

/** Find out who is logged in (on start), then load their workspace. */
export async function checkSession(): Promise<void> {
  try {
    const me = await fetchMe();
    app.user = me?.username ?? null;
    app.admin = me?.admin ?? false;
    if (app.user) await load();
  } catch (e) {
    app.user = null;
    app.error = `Cannot reach the server (${e})`;
  }
}

/** Throws ApiError on failure (401 wrong credentials, 429 locked out). */
export async function logIn(username: string, password: string): Promise<void> {
  const me = await auth.login(username, password);
  resetEtag();
  app.user = me.username;
  app.admin = me.admin ?? false;
  app.error = null;
  await load();
}

export async function logOut(): Promise<void> {
  try {
    await auth.logout();
  } finally {
    loggedOut();
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

/** Open one lane line (the line after a milestone) for editing. */
export function selectLine(milestoneId: string): void {
  app.panel = { kind: 'line', type: 'milestones', id: milestoneId };
}

export function openForm(type: EntityType, opts: { id?: string; preset?: Record<string, unknown>; title?: string } = {}): void {
  app.panel = { kind: 'form', type, ...opts };
}

export function closePanel(): void {
  app.panel = null;
}

/**
 * Whether a lane line (the line after milestone `from`, in state `stateId`) is
 * the one being worked on: the line opened for editing, or every line of a state
 * opened from Settings.
 */
export function isSelectedLine(stateId: string, from: string): boolean {
  const p = app.panel;
  if (!p) return false;
  if (p.kind === 'line') return p.id === from;
  return p.kind === 'view' && p.type === 'states' && p.id === stateId;
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
