// Display helpers for entities of any type.
import type { EntityType, Workspace } from '../api/client';

export const TYPE_LABEL: Record<EntityType, string> = {
  domains: 'Domain',
  groups: 'Group',
  projects: 'Project',
  milestones: 'Milestone',
  references: 'Reference',
  kinds: 'Kind',
  states: 'State',
  reftypes: 'Reference type',
  markers: 'Marker',
};

type AnyEntity = Workspace[EntityType][number];

export function findEntity(ws: Workspace, type: EntityType, id: string): AnyEntity | undefined {
  return (ws[type] as AnyEntity[]).find((e) => e.id === id);
}

/** A short name: group/kind/state/reftype name, project title, "Project › milestone", reference "a → b". */
export function entityName(ws: Workspace, type: EntityType, id: string): string {
  const e = findEntity(ws, type, id) as Record<string, unknown> | undefined;
  if (!e) return id;
  if (type === 'projects') return e.title as string;
  if (type === 'milestones') {
    const p = ws.projects.find((p) => p.id === e.project);
    return `${p?.title ?? e.project} › ${e.title}`;
  }
  if (type === 'references') {
    const rt = ws.reftypes.find((t) => t.id === e.type);
    return `${entityName(ws, 'milestones', e.from as string)} — ${rt?.name ?? e.type} → ${entityName(ws, 'milestones', e.to as string)}`;
  }
  return e.name as string;
}
