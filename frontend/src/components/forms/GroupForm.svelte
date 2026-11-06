<script lang="ts">
  import { untrack } from 'svelte';
  import { api, messagesOf } from '../../api/client';
  import { app, change, select } from '../../state.svelte';
  import ColorInput from '../ColorInput.svelte';
  import DescriptionEditor from '../DescriptionEditor.svelte';
  import FormShell from '../FormShell.svelte';

  let { id }: { id?: string } = $props();
  const existing = untrack(() => (id ? app.ws!.groups.find((g) => g.id === id) : undefined));
  let d = $state({ name: existing?.name ?? '', color: existing?.color ?? '#808080', domain: existing?.domain ?? '', description: '' });
  let errors = $state<string[]>([]);
  let busy = $state(false);

  async function submit() {
    busy = true;
    errors = [];
    try {
      const r = existing
        ? await change(() => api.update('groups', existing.id, { name: d.name, color: d.color, domain: d.domain || null }), `Saved group “${d.name}”.`)
        : await change(() => api.create('groups', { ...d, color: d.color ?? '#808080', domain: d.domain || null }), `Created group “${d.name}”.`);
      select('groups', r.id);
    } catch (e) {
      errors = messagesOf(e);
    } finally {
      busy = false;
    }
  }
</script>

<FormShell title={existing ? 'Edit group' : 'New group'} {errors} {busy} onsubmit={submit} submitLabel={existing ? 'Save' : 'Create'}>
  <label>Name <input bind:value={d.name} required /></label>
  <label>Domain
    <select bind:value={d.domain}>
      <option value="">(none: listed first)</option>
      {#each app.ws?.domains ?? [] as dm}<option value={dm.id}>{dm.name}</option>{/each}
    </select>
  </label>
  <div class="field"><span>Colour</span><ColorInput bind:value={d.color} allowClear={false} /></div>
  {#if !existing}<div class="field"><span>Description</span><DescriptionEditor bind:value={d.description} /></div>{/if}
</FormShell>
