<script lang="ts">
  import { untrack } from 'svelte';
  // Create a project with its first milestone (a fork if `from` is set), or edit one.
  import { api, messagesOf } from '../../api/client';
  import { localToday } from '../../layout/model';
  import { app, change, select } from '../../state.svelte';
  import ColorInput from '../ColorInput.svelte';
  import DescriptionEditor from '../DescriptionEditor.svelte';
  import FormShell from '../FormShell.svelte';
  import LinksEditor from '../LinksEditor.svelte';
  import MilestoneSelect from '../MilestoneSelect.svelte';

  let { id, preset = {}, title }: { id?: string; preset?: Record<string, unknown>; title?: string } = $props();
  const ws = app.ws!;
  const existing = untrack(() => (id ? ws.projects.find((p) => p.id === id) : undefined));
  const p = untrack(() => preset) as { from?: string; group?: string; date?: string };

  let d = $state({
    title: existing?.title ?? '',
    group: existing?.group ?? p.group ?? ws.groups[0]?.id ?? '',
    from: existing?.from ?? p.from ?? null,
    links: $state.snapshot(existing?.links ?? []),
    color: existing?.color ?? null,
    description: '',
    first: { title: '', date: p.date ?? localToday(), kind: ws.kinds[0]?.id ?? '', state: '', planned: false },
  });
  let errors = $state<string[]>([]);
  let busy = $state(false);

  async function submit() {
    busy = true;
    errors = [];
    const fields = { title: d.title, group: d.group, from: d.from || null, links: d.links.filter((l) => l.label || l.url), color: d.color };
    try {
      const r = existing
        ? await change(() => api.update('projects', existing.id, fields), `Saved project “${d.title}”.`)
        : await change(
            () => api.create('projects', { ...fields, description: d.description, first_milestone: { ...d.first, state: d.first.state || null } }),
            d.from ? `Forked “${d.title}”.` : `Created project “${d.title}”.`,
          );
      select('projects', r.id);
    } catch (e) {
      errors = messagesOf(e);
    } finally {
      busy = false;
    }
  }
</script>

<FormShell title={title ?? (existing ? 'Edit project' : 'New project')} {errors} {busy} onsubmit={submit} submitLabel={existing ? 'Save' : 'Create'}>
  {#if !ws.groups.length}
    <p class="muted">Create a group first (Settings, or “Add group” in the toolbar).</p>
  {/if}
  <label>Title <input bind:value={d.title} required /></label>
  <label>Group
    <select bind:value={d.group} required>{#each ws.groups as g}<option value={g.id}>{g.name}</option>{/each}</select>
  </label>
  <label>Forked from
    <MilestoneSelect bind:value={d.from} excludeProject={existing?.id ?? null} placeholder="(not a fork)" />
  </label>
  <div class="field"><span>Links</span><LinksEditor bind:links={d.links} /></div>
  <div class="field"><span>Colour</span><ColorInput bind:value={d.color} /></div>
  {#if !existing}
    <div class="field"><span>Description</span><DescriptionEditor bind:value={d.description} /></div>
    <fieldset>
      <legend>First milestone</legend>
      <label>Title <input bind:value={d.first.title} required placeholder="e.g. draft" /></label>
      <label>Date <input type="date" bind:value={d.first.date} required /></label>
      <label>Kind
        <select bind:value={d.first.kind}>{#each ws.kinds as k}<option value={k.id}>{k.name}</option>{/each}</select>
      </label>
      <label>State
        <select bind:value={d.first.state}>
          <option value="">(default: kind's default, else the fork origin's)</option>
          {#each ws.states as s}<option value={s.id}>{s.name}</option>{/each}
        </select>
      </label>
      <label class="check"><input type="checkbox" bind:checked={d.first.planned} /> Planned</label>
    </fieldset>
  {/if}
</FormShell>
