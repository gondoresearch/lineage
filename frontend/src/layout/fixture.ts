// Test helper: build a Workspace (with `derived` filled in the way the backend does).
import type { Milestone, Project, Workspace } from '../api/client';

type P = Partial<Project> & { id: string; group: string };
type M = Partial<Milestone> & { id: string; date: string };

export function makeWs(spec: {
  groups?: { id: string; color?: string; domain?: string | null }[];
  domains?: Workspace['domains'];
  projects: P[];
  milestones: M[];
  /** text fields are optional here; they default to no text */
  references?: (Omit<Workspace['references'][number], 'text' | 'text_align' | 'text_position' | 'text_orientation' | 'text_size'> & Partial<Workspace['references'][number]>)[];
  settings?: Workspace['settings'];
  markers?: Workspace['markers'];
  kinds?: Partial<Workspace['kinds'][number]>[];
  states?: Partial<Workspace['states'][number]>[];
  reftypes?: Workspace['reftypes'];
}): Workspace {
  const groups = (spec.groups ?? [{ id: 'g' }]).map((g) => ({ name: g.id, color: '#000000', domain: null, description: '', ...g }));
  const projects = spec.projects.map((p) => ({ title: p.id, from: null, links: [], color: null, description: '', ...p })) as Project[];
  const milestones = spec.milestones.map((m) => ({
    project: m.id.split('.')[0],
    title: m.id,
    kind: 'draft',
    state: 'drafting',
    planned: false,
    labels: [],
    merges: [],
    markers: [],
    line_pattern: null,
    line_color: null,
    line_width: null,
    line_opacity: null,
    line_text: '',
    line_text_align: 'center',
    line_text_position: 'above',
    line_text_size: 10,
    links: [],
    color: null,
    description: '',
    ...m,
  })) as Milestone[];
  const kinds = (spec.kinds ?? [{ id: 'draft', shape: 'open-circle' }]).map((k) => ({
    name: k.id!, shape: 'open-circle', size: 1, default_state: null, closes: false, color: null, description: '', ...k,
  })) as Workspace['kinds'];
  const states = (spec.states ?? [
    { id: 'drafting', line: 'solid', waiting_on: 'me' },
    { id: 'review', line: 'dashed', waiting_on: 'others' },
    { id: 'done', line: 'dotted', waiting_on: 'nobody' },
  ]).map((s) => ({ name: s.id!, color: null, opacity: 1, line_width: 2.5, text: '', text_align: 'center', text_position: 'above', text_size: 10, description: '', ...s })) as Workspace['states'];

  const order = new Map(milestones.map((m, i) => [m.id, i]));
  const derivedProjects: Workspace['derived']['projects'] = {};
  const parents: Record<string, string[]> = {};
  const mergeSources = new Set(milestones.flatMap((m) => m.merges ?? []));
  for (const p of projects) {
    const ms = milestones
      .filter((m) => m.project === p.id)
      .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : order.get(a.id)! - order.get(b.id)!));
    const real = ms.filter((m) => !m.planned);
    const head = real[real.length - 1] ?? null;
    derivedProjects[p.id] = {
      milestones: ms.map((m) => m.id),
      head: head?.id ?? null,
      current_state: head && !kinds.find((k) => k.id === head.kind)?.closes ? (head.state ?? null) : null,
      merged: !!head && mergeSources.has(head.id),
      closed: !!head && !!kinds.find((k) => k.id === head.kind)?.closes,
    };
    ms.forEach((m, i) => {
      parents[m.id] = [...(i > 0 ? [ms[i - 1].id] : p.from ? [p.from] : []), ...(m.merges ?? [])];
    });
  }
  return {
    domains: spec.domains ?? [],
    settings: spec.settings ?? { fork_color: null, merge_color: null, fork_width: 1.8, merge_width: 1.8 },
    groups,
    projects,
    milestones,
    references: (spec.references ?? []).map((r) => ({ text: '', text_align: 'center', text_position: 'above', text_orientation: 'horizontal', text_size: 10, ...r })) as Workspace['references'],
    kinds,
    states,
    reftypes: spec.reftypes ?? [
      { id: 'builds-on', name: 'builds on', directed: true, line: 'dashed', opacity: 1, line_width: 1.4, color: null, description: '' },
      { id: 'companion', name: 'companion', directed: false, line: 'dotted', opacity: 0.5, line_width: 1.4, color: null, description: '' },
    ],
    markers: spec.markers ?? [],
    derived: { projects: derivedProjects, parents },
  };
}
