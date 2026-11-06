// Small fetch wrapper. Types come from schema.d.ts (generated: npm run gen-api).
import type { components } from './schema';

export type Schemas = components['schemas'];
export type Workspace = Schemas['WorkspaceOut'];
export type Group = Schemas['Group'];
export type Project = Schemas['Project'];
export type Milestone = Schemas['Milestone'];
export type Reference = Schemas['Reference'];
export type Kind = Schemas['Kind'];
export type State = Schemas['State'];
export type RefType = Schemas['RefType'];
export type Settings = Schemas['Settings'];
export type Marker = Schemas['Marker'];
export type Domain = Schemas['Domain'];

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    const errors = (body as { errors?: string[] } | null)?.errors;
    super(errors?.join('\n') ?? `HTTP ${status}`);
  }
}

let etag: string | null = null;

/** The workspace, or null if unchanged since the last call (304). */
export async function fetchWorkspace(): Promise<Workspace | null> {
  const res = await fetch('/api/workspace', {
    headers: etag ? { 'If-None-Match': etag } : {},
  });
  if (res.status === 304) return null;
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body);
  etag = res.headers.get('ETag');
  return body as Workspace;
}

// ------------------------------------------------------------------ writes

export type EntityType = 'domains' | 'groups' | 'projects' | 'milestones' | 'references' | 'kinds' | 'states' | 'reftypes' | 'markers';

interface CreateBody {
  domains: Schemas['DomainCreate'];
  groups: Schemas['GroupCreate'];
  projects: Schemas['ProjectCreate'];
  milestones: Schemas['MilestoneCreate'];
  references: Schemas['ReferenceCreate'];
  kinds: Schemas['KindCreate'];
  states: Schemas['StateCreate'];
  reftypes: Schemas['RefTypeCreate'];
  markers: Schemas['MarkerCreate'];
}

interface PatchBody {
  domains: Schemas['DomainPatch'];
  groups: Schemas['GroupPatch'];
  projects: Schemas['ProjectPatch'];
  milestones: Schemas['MilestonePatch'];
  references: Schemas['ReferencePatch'];
  kinds: Schemas['KindPatch'];
  states: Schemas['StatePatch'];
  reftypes: Schemas['RefTypePatch'];
  markers: Schemas['MarkerPatch'];
}

export type DryRun = Schemas['DryRunOut'];
export type Blocker = Schemas['Blocker'];

export async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

const path = (type: EntityType, id: string) => `/api/${type}/${encodeURIComponent(id)}`;

export const api = {
  create: <K extends EntityType>(type: K, body: CreateBody[K]) =>
    request<{ id: string }>('POST', `/api/${type}`, body),
  update: <K extends EntityType>(type: K, id: string, body: PatchBody[K]) =>
    request<{ id: string }>('PATCH', path(type, id), body),
  remove: (type: EntityType, id: string) => request<void>('DELETE', path(type, id)),
  dryRun: (type: EntityType, id: string) => request<DryRun>('DELETE', `${path(type, id)}?dry_run=true`),
  undo: () => request<void>('POST', '/api/undo'),
  updateSettings: (body: Schemas['SettingsPatch']) => request<Settings>('PATCH', '/api/settings', body),
};

/** Human-readable messages from any error thrown by `request`. */
export function messagesOf(e: unknown): string[] {
  if (e instanceof ApiError) {
    const errors = (e.body as { errors?: string[] } | null)?.errors;
    return errors?.length ? errors : [e.message];
  }
  return [String(e)];
}

// ------------------------------------------------------------------ version, backup, restore

export async function fetchVersion(): Promise<string> {
  return (await request<Schemas['VersionOut']>('GET', '/api/version')).version;
}

export type RestoreResult =
  | { ok: true; result: Schemas['RestoreOut'] }
  | { ok: false; mismatch: Schemas['VersionMismatchOut'] };

/** Upload a backup and replace the whole workspace with it. A version mismatch is
 * returned (not thrown) so the caller can ask the user and retry with force. */
export async function restoreBackup(file: Blob, force = false): Promise<RestoreResult> {
  const res = await fetch(`/api/restore?force=${force}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/gzip' },
    body: file,
  });
  const body = await res.json().catch(() => null);
  if (res.status === 409 && body?.backup_version) return { ok: false, mismatch: body };
  if (!res.ok) throw new ApiError(res.status, body);
  return { ok: true, result: body };
}
