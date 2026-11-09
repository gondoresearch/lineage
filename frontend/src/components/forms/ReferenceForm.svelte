<script lang="ts">
  import { localNow } from '../../layout/model';
  // Create a reference from a milestone (type, then click the target milestone on
  // the timeline), or edit an existing reference's type and colour.
  import { untrack } from 'svelte';
  import { api, messagesOf } from '../../api/client';
  import { entityName } from '../../lib/entities';
  import { app, change, select, startPicking, stopPicking } from '../../state.svelte';
  import ColorInput from '../ColorInput.svelte';
  import DescriptionEditor from '../DescriptionEditor.svelte';
  import FormShell from '../FormShell.svelte';
  import LineTextFields from '../LineTextFields.svelte';

  let { id, preset = {} }: { id?: string; preset?: Record<string, unknown> } = $props();
  const ws = app.ws!;
  const existing = untrack(() => (id ? ws.references.find((r) => r.id === id) : undefined));
  const from = existing?.from ?? untrack(() => preset.from as string);

  let d = $state({
    type: existing?.type ?? ws.reftypes[0]?.id ?? '',
    to: '',
    color: existing?.color ?? null,
    text: existing?.text ?? '',
    text_align: existing?.text_align ?? ('center' as 'left' | 'center' | 'right'),
    text_position: existing?.text_position ?? ('above' as 'above' | 'middle' | 'below'),
    text_orientation: existing?.text_orientation ?? ('horizontal' as 'horizontal' | 'along'),
    text_size: existing?.text_size ?? 10,
    created: existing?.created ?? localNow(),
    description: '',
  });
  const directed = $derived(ws.reftypes.find((t) => t.id === d.type)?.directed);
  const picking = $derived(!!app.picking);
  let errors = $state<string[]>([]);
  let busy = $state(false);

  function pick() {
    errors = [];
    startPicking({
      prompt: `Click the milestone that “${entityName(ws, 'milestones', from)}” refers to.`,
      exclude: from,
      onPick: (m) => {
        d.to = m;
        stopPicking();
      },
    });
  }

  // A new reference starts by picking its target; stop picking when the form closes.
  $effect(() => {
    if (!existing) untrack(pick);
    return stopPicking;
  });

  async function submit() {
    if (!existing && !d.to) {
      errors = ['Click the target milestone on the timeline first.'];
      return;
    }
    busy = true;
    errors = [];
    const text = { text: d.text, text_align: d.text_align, text_position: d.text_position, text_orientation: d.text_orientation, text_size: d.text_size };
    try {
      const r = existing
        ? await change(() => api.update('references', existing.id, { type: d.type, color: d.color, created: d.created || null, ...text }), 'Saved reference.')
        : await change(() => api.create('references', { type: d.type, from, to: d.to, color: d.color, created: d.created || null, ...text, description: d.description }), 'Added reference.');
      select('references', r.id);
    } catch (e) {
      errors = messagesOf(e);
    } finally {
      busy = false;
    }
  }
</script>

<FormShell title={existing ? 'Edit reference' : 'Add reference'} {errors} {busy} onsubmit={submit} submitLabel={existing ? 'Save' : 'Add'}>
  <div class="field"><span>From</span>{entityName(ws, 'milestones', from)}</div>
  <label>Type
    <select bind:value={d.type}>{#each ws.reftypes as t}<option value={t.id}>{t.name}</option>{/each}</select>
  </label>
  {#if existing}
    <div class="field"><span>To</span>{entityName(ws, 'milestones', existing.to)}</div>
  {:else}
    <div class="field">
      <span>To</span>
      <div class="target" class:waiting={picking}>
        {#if d.to}
          <strong>{entityName(ws, 'milestones', d.to)}</strong>
        {:else if picking}
          <span class="muted">Click a milestone on the timeline…</span>
        {:else}
          <span class="muted">No target yet.</span>
        {/if}
        {#if !picking}
          <button type="button" onclick={pick}>{d.to ? 'Pick again' : 'Pick on timeline'}</button>
        {/if}
      </div>
    </div>
    {#if directed}<p class="muted small">The source milestone builds on the target (the arrow points at the target).</p>{/if}
  {/if}
  <LineTextFields bind:text={d.text} bind:align={d.text_align} bind:position={d.text_position} bind:orientation={d.text_orientation} bind:size={d.text_size}
    alongLabels={['near the source', 'middle', 'near the target']} />
  <div class="field"><span>Colour</span><ColorInput bind:value={d.color} /></div>
  <label>Recorded <input type="datetime-local" bind:value={d.created} /></label>
  {#if !existing}<div class="field"><span>Description</span><DescriptionEditor bind:value={d.description} /></div>{/if}
</FormShell>

<style>
  .target {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    min-height: 2.1rem;
    padding: 0.3rem 0.3rem 0.3rem 0.55rem;
    border: 1px solid var(--line);
    border-radius: 6px;
  }
  .target.waiting {
    border: 1.5px dashed var(--accent);
  }
</style>
