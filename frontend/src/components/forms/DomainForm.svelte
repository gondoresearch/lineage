<script lang="ts">
  import { untrack } from 'svelte';
  import { api, messagesOf } from '../../api/client';
  import { app, change, select } from '../../state.svelte';
  import ColorInput from '../ColorInput.svelte';
  import DescriptionEditor from '../DescriptionEditor.svelte';
  import FormShell from '../FormShell.svelte';

  let { id }: { id?: string } = $props();
  const existing = untrack(() => (id ? (app.ws!.domains ?? []).find((d) => d.id === id) : undefined));
  let d = $state({ name: existing?.name ?? '', color: existing?.color ?? null, description: '' });
  let errors = $state<string[]>([]);
  let busy = $state(false);

  async function submit() {
    busy = true;
    errors = [];
    try {
      const r = existing
        ? await change(() => api.update('domains', existing.id, { name: d.name, color: d.color }), `Saved domain “${d.name}”.`)
        : await change(() => api.create('domains', { ...d }), `Created domain “${d.name}”.`);
      select('domains', r.id);
    } catch (e) {
      errors = messagesOf(e);
    } finally {
      busy = false;
    }
  }
</script>

<FormShell title={existing ? 'Edit domain' : 'New domain'} {errors} {busy} onsubmit={submit} submitLabel={existing ? 'Save' : 'Create'}>
  <label>Name <input bind:value={d.name} required placeholder="e.g. Research" /></label>
  <div class="field"><span>Colour <span class="muted">(of its heading)</span></span><ColorInput bind:value={d.color} /></div>
  {#if !existing}<div class="field"><span>Description</span><DescriptionEditor bind:value={d.description} /></div>{/if}
</FormShell>
