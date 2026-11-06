<script lang="ts">
  import { untrack } from 'svelte';
  import { api, messagesOf, type Schemas } from '../../api/client';
  import { MARKER_NEUTRAL } from '../../layout/colors';
  import { app, change, select } from '../../state.svelte';
  import ColorInput from '../ColorInput.svelte';
  import DescriptionEditor from '../DescriptionEditor.svelte';
  import FormShell from '../FormShell.svelte';
  import MarkerIcon from '../MarkerIcon.svelte';

  type Icon = Schemas['Marker']['icon'];
  const ICONS: Icon[] = ['warning', 'question', 'chain', 'flag', 'pin', 'clock', 'lock', 'check', 'info'];

  let { id }: { id?: string } = $props();
  const existing = untrack(() => (id ? (app.ws!.markers ?? []).find((m) => m.id === id) : undefined));
  let d = $state({
    name: existing?.name ?? '',
    icon: existing?.icon ?? ('warning' as Icon),
    color: existing?.color ?? null,
    description: '',
  });
  let errors = $state<string[]>([]);
  let busy = $state(false);

  async function submit() {
    busy = true;
    errors = [];
    const body = { name: d.name, icon: d.icon, color: d.color };
    try {
      const r = existing
        ? await change(() => api.update('markers', existing.id, body), `Saved marker “${d.name}”.`)
        : await change(() => api.create('markers', { ...body, description: d.description }), `Created marker “${d.name}”.`);
      select('markers', r.id);
    } catch (e) {
      errors = messagesOf(e);
    } finally {
      busy = false;
    }
  }
</script>

<FormShell title={existing ? 'Edit marker' : 'New marker'} {errors} {busy} onsubmit={submit} submitLabel={existing ? 'Save' : 'Create'}>
  <label>Name <input bind:value={d.name} required placeholder="e.g. needs data" /></label>
  <div class="field">
    <span>Icon</span>
    <div class="icons" role="radiogroup" aria-label="Icon">
      {#each ICONS as icon}
        <button type="button" class="icon" class:on={d.icon === icon} role="radio" aria-checked={d.icon === icon}
          title={icon} onclick={() => {
            d.icon = icon;
          }}>
          <svg width="22" height="22" aria-hidden="true"><MarkerIcon {icon} x={11} y={11} size={16} color={d.color ?? MARKER_NEUTRAL} /></svg>
        </button>
      {/each}
    </div>
  </div>
  <div class="field"><span>Colour</span><ColorInput bind:value={d.color} /></div>
  {#if !existing}<div class="field"><span>Description</span><DescriptionEditor bind:value={d.description} /></div>{/if}
</FormShell>

<style>
  .icons {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
  }
  .icon {
    padding: 3px;
    line-height: 0;
  }
  .icon.on {
    border-color: var(--accent);
    box-shadow: 0 0 0 1px var(--accent);
    background: var(--bg);
  }
</style>
