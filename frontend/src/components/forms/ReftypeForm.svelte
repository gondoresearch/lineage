<script lang="ts">
  import { untrack } from 'svelte';
  import { api, messagesOf } from '../../api/client';
  import { app, change, select } from '../../state.svelte';
  import ColorInput from '../ColorInput.svelte';
  import LineSample from '../LineSample.svelte';
  import { LINES, type Line } from '../lines';
  import { NEUTRAL } from '../../layout/colors';
  import DescriptionEditor from '../DescriptionEditor.svelte';
  import FormShell from '../FormShell.svelte';

  let { id }: { id?: string } = $props();
  const existing = untrack(() => (id ? app.ws!.reftypes.find((t) => t.id === id) : undefined));
  let d = $state({
    name: existing?.name ?? '',
    directed: existing?.directed ?? true,
    line: existing?.line ?? ('dashed' as Line),
    opacity: existing?.opacity ?? 1,
    line_width: existing?.line_width ?? 1.4,
    color: existing?.color ?? null,
    description: '',
  });
  let errors = $state<string[]>([]);
  let busy = $state(false);

  async function submit() {
    busy = true;
    errors = [];
    const body = { name: d.name, directed: d.directed, line: d.line, opacity: d.opacity, line_width: d.line_width, color: d.color };
    try {
      const r = existing
        ? await change(() => api.update('reftypes', existing.id, body), `Saved reference type “${d.name}”.`)
        : await change(() => api.create('reftypes', { ...body, description: d.description }), `Created reference type “${d.name}”.`);
      select('reftypes', r.id);
    } catch (e) {
      errors = messagesOf(e);
    } finally {
      busy = false;
    }
  }
</script>

<FormShell title={existing ? 'Edit reference type' : 'New reference type'} {errors} {busy} onsubmit={submit} submitLabel={existing ? 'Save' : 'Create'}>
  <label>Name <input bind:value={d.name} required /></label>
  <label class="check"><input type="checkbox" bind:checked={d.directed} /> Directed (arrow points at the work built on)</label>
  <label>Line
    <select bind:value={d.line}>{#each LINES as l}<option value={l.value}>{l.label}</option>{/each}</select>
  </label>
  <label>Opacity
    <span class="opacity">
      <input type="range" min="0.1" max="1" step="0.05" bind:value={d.opacity} />
      <span>{Math.round(d.opacity * 100)}%</span>
      <LineSample line={d.line} color={d.color ?? NEUTRAL} arrow={d.directed} opacity={d.opacity} thickness={d.line_width} width={60} />
    </span>
  </label>
  <label>Thickness
    <span class="opacity">
      <input type="range" min="0.5" max="8" step="0.5" bind:value={d.line_width} />
      <span>{d.line_width} px</span>
    </span>
  </label>
  <div class="field"><span>Colour</span><ColorInput bind:value={d.color} /></div>
  {#if !existing}<div class="field"><span>Description</span><DescriptionEditor bind:value={d.description} /></div>{/if}
</FormShell>
