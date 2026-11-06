<script lang="ts">
  import { untrack } from 'svelte';
  import { api, messagesOf } from '../../api/client';
  import { app, change, select } from '../../state.svelte';
  import ColorInput from '../ColorInput.svelte';
  import DescriptionEditor from '../DescriptionEditor.svelte';
  import FormShell from '../FormShell.svelte';
  import NodeShape from '../NodeShape.svelte';
  import { NEUTRAL } from '../../layout/colors';

  const SHAPES = [
    'open-circle',
    'filled-circle',
    'diamond',
    'filled-diamond',
    'square',
    'filled-square',
    'triangle',
    'filled-triangle',
    'star',
    'filled-star',
    'cross',
  ] as const;
  let { id }: { id?: string } = $props();
  const ws = app.ws!;
  const existing = untrack(() => (id ? ws.kinds.find((k) => k.id === id) : undefined));
  let d = $state({
    name: existing?.name ?? '',
    shape: existing?.shape ?? ('open-circle' as (typeof SHAPES)[number]),
    size: existing?.size ?? 1,
    default_state: existing?.default_state ?? '',
    color: existing?.color ?? null,
    description: '',
  });
  let errors = $state<string[]>([]);
  let busy = $state(false);

  async function submit() {
    busy = true;
    errors = [];
    const body = { name: d.name, shape: d.shape, size: d.size, default_state: d.default_state || null, color: d.color };
    try {
      const r = existing
        ? await change(() => api.update('kinds', existing.id, body), `Saved kind “${d.name}”.`)
        : await change(() => api.create('kinds', { ...body, description: d.description }), `Created kind “${d.name}”.`);
      select('kinds', r.id);
    } catch (e) {
      errors = messagesOf(e);
    } finally {
      busy = false;
    }
  }
</script>

<FormShell title={existing ? 'Edit kind' : 'New kind'} {errors} {busy} onsubmit={submit} submitLabel={existing ? 'Save' : 'Create'}>
  <label>Name <input bind:value={d.name} required /></label>
  <label>Shape
    <select bind:value={d.shape}>{#each SHAPES as s}<option value={s}>{s}</option>{/each}</select>
  </label>
  <label>Size
    <span class="opacity">
      <input type="range" min="0.5" max="2" step="0.1" bind:value={d.size} />
      <span>{Math.round(d.size * 100)}%</span>
      <svg width="28" height="28" aria-hidden="true"><NodeShape shape={d.shape} x={14} y={14} r={6 * d.size} color={d.color ?? NEUTRAL} /></svg>
    </span>
  </label>
  <label>Default state
    <select bind:value={d.default_state}>
      <option value="">(none: inherit the previous milestone's state)</option>
      {#each ws.states as s}<option value={s.id}>{s.name}</option>{/each}
    </select>
  </label>
  <div class="field"><span>Colour</span><ColorInput bind:value={d.color} /></div>
  {#if !existing}<div class="field"><span>Description</span><DescriptionEditor bind:value={d.description} /></div>{/if}
</FormShell>
