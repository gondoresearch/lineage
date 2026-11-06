<script lang="ts">
  import { untrack } from 'svelte';
  import { api, messagesOf, type EntityType } from '../../api/client';
  import { entityName, findEntity, TYPE_LABEL } from '../../lib/entities';
  import { app, change, select } from '../../state.svelte';
  import DescriptionEditor from '../DescriptionEditor.svelte';
  import FormShell from '../FormShell.svelte';

  let { type, id }: { type: EntityType; id: string } = $props();
  const ws = app.ws!;
  // Initial value only: the panel remounts this form when it switches entity.
  let text = $state(untrack(() => (findEntity(ws, type, id) as { description?: string } | undefined)?.description ?? ''));
  let errors = $state<string[]>([]);
  let busy = $state(false);

  async function submit() {
    busy = true;
    errors = [];
    try {
      await change(() => api.update(type, id, { description: text }), `Saved description of ${TYPE_LABEL[type].toLowerCase()} “${entityName(ws, type, id)}”.`);
      select(type, id);
    } catch (e) {
      errors = messagesOf(e);
    } finally {
      busy = false;
    }
  }
</script>

<FormShell title="Description: {entityName(ws, type, id)}" {errors} {busy} onsubmit={submit} oncancel={() => select(type, id)}>
  <DescriptionEditor bind:value={text} />
</FormShell>
