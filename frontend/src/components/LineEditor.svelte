<script lang="ts">
  // Edits one lane line: the line after milestone `id`. Its state, look and text
  // are stored on that milestone; nothing here changes the state for other lines.
  import { untrack } from 'svelte';
  import { api, messagesOf } from '../api/client';
  import { colors, NEUTRAL } from '../layout/colors';
  import { indexWorkspace } from '../layout/model';
  import { entityName } from '../lib/entities';
  import { app, change, closePanel } from '../state.svelte';
  import ColorInput from './ColorInput.svelte';
  import EntityLink from './EntityLink.svelte';
  import FormShell from './FormShell.svelte';
  import LineSample from './LineSample.svelte';
  import LineTextFields from './LineTextFields.svelte';
  import { LINES, type Line } from './lines';

  let { id }: { id: string } = $props();
  const ws = $derived(app.ws!);
  const m = untrack(() => app.ws!.milestones.find((x) => x.id === id)!);
  const next = untrack(() => {
    const order = app.ws!.derived.projects[m.project]?.milestones ?? [];
    const i = order.indexOf(id);
    return i >= 0 && i + 1 < order.length ? order[i + 1] : null;
  });

  let d = $state({
    state: m.state ?? '',
    line_pattern: (m.line_pattern ?? null) as Line | null,
    line_color: m.line_color ?? null,
    line_width: m.line_width ?? null,
    line_opacity: m.line_opacity ?? null,
    line_text: m.line_text ?? '',
    line_text_align: m.line_text_align ?? ('center' as 'left' | 'center' | 'right'),
    line_text_position: m.line_text_position ?? ('above' as 'above' | 'middle' | 'below'),
    line_text_size: m.line_text_size ?? 10,
  });
  let errors = $state<string[]>([]);
  let busy = $state(false);

  // The state's look, shown wherever this line has no setting of its own.
  const st = $derived(ws.states.find((s) => s.id === d.state));
  const look = $derived({
    line: d.line_pattern ?? st?.line ?? 'solid',
    color: d.line_color ?? colors(indexWorkspace(ws)).segment({ ...m, state: d.state || null, line_color: null }),
    width: d.line_width ?? st?.line_width ?? 2.5,
    opacity: d.line_opacity ?? st?.opacity ?? 1,
  });

  async function submit() {
    busy = true;
    errors = [];
    try {
      await change(
        () => api.update('milestones', id, { ...d, state: d.state || null }),
        `Saved the line after “${entityName(ws, 'milestones', id)}”.`,
      );
    } catch (e) {
      errors = messagesOf(e);
    } finally {
      busy = false;
    }
  }
</script>

<FormShell title="Line" {errors} {busy} onsubmit={submit} oncancel={closePanel}>
  <p class="where">
    After <EntityLink type="milestones" id={id} />{#if next}, until <EntityLink type="milestones" id={next} />{:else}, until today{/if}.
  </p>

  <div class="preview" aria-hidden="true">
    <LineSample line={look.line} color={look.color ?? NEUTRAL} opacity={look.opacity} thickness={look.width} width={150} />
  </div>

  <label>State
    <select bind:value={d.state}>{#each ws.states as s}<option value={s.id}>{s.name}</option>{/each}</select>
  </label>

  <fieldset>
    <legend>Look of this line <span class="muted">(unset = the state's)</span></legend>
    <label>Pattern
      <select bind:value={d.line_pattern}>
        <option value={null}>state's ({LINES.find((l) => l.value === (st?.line ?? 'solid'))?.label})</option>
        {#each LINES as l}<option value={l.value}>{l.label}</option>{/each}
      </select>
    </label>
    <div class="field"><span>Colour</span><ColorInput bind:value={d.line_color} /></div>
    <label>Thickness
      <span class="opacity">
        <input type="range" min="0.5" max="8" step="0.5" value={look.width}
          oninput={(e) => {
            d.line_width = Number(e.currentTarget.value);
          }} />
        <span>{look.width} px{d.line_width === null ? " (state's)" : ''}</span>
        {#if d.line_width !== null}<button type="button" onclick={() => {
          d.line_width = null;
        }}>Reset</button>{/if}
      </span>
    </label>
    <label>Opacity
      <span class="opacity">
        <input type="range" min="0.1" max="1" step="0.05" value={look.opacity}
          oninput={(e) => {
            d.line_opacity = Number(e.currentTarget.value);
          }} />
        <span>{Math.round(look.opacity * 100)}%{d.line_opacity === null ? " (state's)" : ''}</span>
        {#if d.line_opacity !== null}<button type="button" onclick={() => {
          d.line_opacity = null;
        }}>Reset</button>{/if}
      </span>
    </label>
  </fieldset>

  <LineTextFields bind:text={d.line_text} bind:align={d.line_text_align} bind:position={d.line_text_position}
    bind:size={d.line_text_size} label="Text on this line" />
</FormShell>

<style>
  .where {
    margin: -0.2rem 0 0;
  }
  .preview {
    padding: 0.5rem 0.6rem;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--panel);
  }
</style>
