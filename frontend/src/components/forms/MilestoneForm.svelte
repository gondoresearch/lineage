<script lang="ts">
  import { untrack } from 'svelte';
  // Create (optionally as a merge: preset.merges) or edit a milestone.
  import { api, messagesOf } from '../../api/client';
  import { localNow } from '../../layout/model';
  import { entityName } from '../../lib/entities';
  import { app, change, select } from '../../state.svelte';
  import ColorInput from '../ColorInput.svelte';
  import DescriptionEditor from '../DescriptionEditor.svelte';
  import FormShell from '../FormShell.svelte';
  import LinksEditor from '../LinksEditor.svelte';
  import MilestoneSelect from '../MilestoneSelect.svelte';
  import MarkerIcon from '../MarkerIcon.svelte';
  import LineTextFields from '../LineTextFields.svelte';
  import { colors } from '../../layout/colors';
  import { indexWorkspace } from '../../layout/model';

  let { id, preset = {}, title }: { id?: string; preset?: Record<string, unknown>; title?: string } = $props();
  const ws = app.ws!;
  const existing = untrack(() => (id ? ws.milestones.find((m) => m.id === id) : undefined));
  const p = untrack(() => preset) as { project?: string; merges?: string[]; at?: string };
  const mergeSources = existing ? [] : (p.merges ?? []);
  const sourceProjects = mergeSources.map((s) => ws.milestones.find((m) => m.id === s)?.project);

  let d = $state({
    project: existing?.project ?? p.project ?? '',
    title: existing?.title ?? '',
    at: existing?.at ?? p.at ?? localNow(),
    kind: existing?.kind ?? ws.kinds[0]?.id ?? '',
    state: existing?.state ?? '',
    planned: existing?.planned ?? false,
    labels: (existing?.labels ?? []).join(', '),
    merges: [...(existing?.merges ?? mergeSources)],
    markers: [...(existing?.markers ?? [])],
    line_text: existing?.line_text ?? '',
    line_text_align: existing?.line_text_align ?? ('center' as 'left' | 'center' | 'right'),
    line_text_position: existing?.line_text_position ?? ('above' as 'above' | 'middle' | 'below'),
    line_text_size: existing?.line_text_size ?? 10,
    links: $state.snapshot(existing?.links ?? []),
    color: existing?.color ?? null,
    description: '',
  });
  const closes = $derived(!!ws.kinds.find((k) => k.id === d.kind)?.closes);
  let errors = $state<string[]>([]);
  let busy = $state(false);

  async function submit() {
    busy = true;
    errors = [];
    const common = {
      title: d.title,
      at: d.at,
      kind: d.kind,
      planned: d.planned,
      labels: d.labels.split(',').map((s) => s.trim()).filter(Boolean),
      merges: d.merges,
      markers: d.markers,
      line_text: d.line_text,
      line_text_align: d.line_text_align,
      line_text_position: d.line_text_position,
      line_text_size: d.line_text_size,
      links: d.links.filter((l) => l.label || l.url),
      color: d.color,
    };
    try {
      const r = existing
        ? await change(() => api.update('milestones', existing.id, { ...common, state: closes ? null : d.state || null }), `Saved milestone “${d.title}”.`)
        : await change(
            () => api.create('milestones', { ...common, project: d.project, state: closes ? null : d.state || null, description: d.description }),
            mergeSources.length ? `Merged into “${entityName(ws, 'projects', d.project)}”.` : `Created milestone “${d.title}”.`,
          );
      select('milestones', r.id);
    } catch (e) {
      errors = messagesOf(e);
    } finally {
      busy = false;
    }
  }
</script>

<FormShell title={title ?? (existing ? 'Edit milestone' : 'New milestone')} {errors} {busy} onsubmit={submit} submitLabel={existing ? 'Save' : 'Create'}>
  {#if existing}
    <div class="field"><span>Project</span>{entityName(ws, 'projects', existing.project)}</div>
  {:else}
    <label>{mergeSources.length ? 'Merge into project' : 'Project'}
      <select bind:value={d.project} required>
        <option value="">Choose a project…</option>
        {#each ws.projects.filter((x) => !sourceProjects.includes(x.id)) as proj}<option value={proj.id}>{proj.title}</option>{/each}
      </select>
    </label>
  {/if}
  <label>Title <input bind:value={d.title} required placeholder="e.g. v2" /></label>
  <label>Date and time <input type="datetime-local" bind:value={d.at} required /></label>
  <label>Kind
    <select bind:value={d.kind}>{#each ws.kinds as k}<option value={k.id}>{k.name}</option>{/each}</select>
  </label>
  {#if closes}
    <p class="muted small">This kind closes the project: the milestone has no state and the lane ends here.</p>
  {:else}
  <label>State
    <select bind:value={d.state}>
      {#if !existing}<option value="">(default: kind's default, else previous state)</option>{/if}
      {#each ws.states as s}<option value={s.id}>{s.name}</option>{/each}
    </select>
  </label>
  {/if}
  <label class="check"><input type="checkbox" bind:checked={d.planned} /> Planned</label>
  <label>Labels <input bind:value={d.labels} placeholder="comma-separated" /></label>
  <div class="field">
    <span>Merges</span>
    {#each d.merges as m, i}
      <div class="chip">{entityName(ws, 'milestones', m)} <button type="button" aria-label="Remove" onclick={() => d.merges.splice(i, 1)}>×</button></div>
    {/each}
    {#key d.merges.length}
      <MilestoneSelect value={null} excludeProject={d.project || null} exclude={d.merges} placeholder="Add a merge source…" onpick={(m) => d.merges.push(m)} />
    {/key}
  </div>
  {#if (ws.markers ?? []).length}
    {@const c = colors(indexWorkspace(ws))}
    <div class="field">
      <span>Markers</span>
      <div class="marker-choices">
        {#each ws.markers ?? [] as mk}
          <label class="check">
            <input type="checkbox" checked={d.markers.includes(mk.id)}
              onchange={(e) => {
                if (e.currentTarget.checked) d.markers.push(mk.id);
                else d.markers.splice(d.markers.indexOf(mk.id), 1);
              }} />
            <svg width="14" height="14" aria-hidden="true"><MarkerIcon icon={mk.icon} x={7} y={7} size={12} color={c.marker(mk)} /></svg>
            {mk.name}
          </label>
        {/each}
      </div>
    </div>
  {/if}
  <LineTextFields bind:text={d.line_text} bind:align={d.line_text_align} bind:position={d.line_text_position}
    bind:size={d.line_text_size} label="Text on the line after this milestone" />
  <div class="field"><span>Links</span><LinksEditor bind:links={d.links} /></div>
  <div class="field"><span>Colour</span><ColorInput bind:value={d.color} /></div>
  {#if !existing}<div class="field"><span>Description</span><DescriptionEditor bind:value={d.description} /></div>{/if}
</FormShell>
