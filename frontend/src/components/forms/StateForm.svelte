<script lang="ts">
  import { untrack } from 'svelte';
  import { api, messagesOf } from '../../api/client';
  import { app, change, select } from '../../state.svelte';
  import ColorInput from '../ColorInput.svelte';
  import LineSample from '../LineSample.svelte';
  import LineTextFields from '../LineTextFields.svelte';
  import { LINES, type Line } from '../lines';
  import { NEUTRAL } from '../../layout/colors';
  import DescriptionEditor from '../DescriptionEditor.svelte';
  import FormShell from '../FormShell.svelte';

  let { id }: { id?: string } = $props();
  const existing = untrack(() => (id ? app.ws!.states.find((s) => s.id === id) : undefined));
  let d = $state({
    name: existing?.name ?? '',
    line: existing?.line ?? ('solid' as Line),
    opacity: existing?.opacity ?? 1,
    line_width: existing?.line_width ?? 2.5,
    text: existing?.text ?? '',
    text_align: existing?.text_align ?? ('center' as 'left' | 'center' | 'right'),
    text_position: existing?.text_position ?? ('above' as 'above' | 'middle' | 'below'),
    text_size: existing?.text_size ?? 10,
    waiting_on: existing?.waiting_on ?? ('me' as 'me' | 'others' | 'nobody'),
    color: existing?.color ?? null,
    description: '',
  });
  let errors = $state<string[]>([]);
  let busy = $state(false);

  async function submit() {
    busy = true;
    errors = [];
    const body = {
      name: d.name,
      line: d.line,
      opacity: d.opacity,
      line_width: d.line_width,
      text: d.text,
      text_align: d.text_align,
      text_position: d.text_position,
      text_size: d.text_size,
      waiting_on: d.waiting_on,
      color: d.color,
    };
    try {
      const r = existing
        ? await change(() => api.update('states', existing.id, body), `Saved state “${d.name}”.`)
        : await change(() => api.create('states', { ...body, description: d.description }), `Created state “${d.name}”.`);
      select('states', r.id);
    } catch (e) {
      errors = messagesOf(e);
    } finally {
      busy = false;
    }
  }
</script>

<FormShell title={existing ? 'Edit state' : 'New state'} {errors} {busy} onsubmit={submit} submitLabel={existing ? 'Save' : 'Create'}>
  <label>Name <input bind:value={d.name} required /></label>
  <label>Line
    <select bind:value={d.line}>{#each LINES as l}<option value={l.value}>{l.label}</option>{/each}</select>
  </label>
  <label>Opacity
    <span class="opacity">
      <input type="range" min="0.1" max="1" step="0.05" bind:value={d.opacity} />
      <span>{Math.round(d.opacity * 100)}%</span>
      <LineSample line={d.line} color={d.color ?? NEUTRAL} opacity={d.opacity} thickness={d.line_width} width={60} />
    </span>
  </label>
  <label>Thickness
    <span class="opacity">
      <input type="range" min="0.5" max="8" step="0.5" bind:value={d.line_width} />
      <span>{d.line_width} px</span>
    </span>
  </label>
  <LineTextFields bind:text={d.text} bind:align={d.text_align} bind:position={d.text_position} bind:size={d.text_size}
    label="Default text on every line in this state" />
  <p class="muted small">To label just one line, click it on the timeline (or edit the milestone it follows).</p>
  <label>Waiting on
    <select bind:value={d.waiting_on}>
      <option value="me">me</option><option value="others">others</option><option value="nobody">nobody (inactive)</option>
    </select>
  </label>
  <div class="field"><span>Colour</span><ColorInput bind:value={d.color} /></div>
  {#if !existing}<div class="field"><span>Description</span><DescriptionEditor bind:value={d.description} /></div>{/if}
</FormShell>
