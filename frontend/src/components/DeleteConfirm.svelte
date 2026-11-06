<script lang="ts">
  import { untrack } from 'svelte';
  // Dry run first; then list what would be removed, or the blockers.
  import { api, messagesOf, type DryRun, type EntityType } from '../api/client';
  import { entityName, TYPE_LABEL } from '../lib/entities';
  import { app, change, closePanel, select } from '../state.svelte';
  import EntityLink from './EntityLink.svelte';

  let { type, id }: { type: EntityType; id: string } = $props();
  const ws = app.ws!;
  const name = untrack(() => entityName(ws, type, id));
  let plan = $state<DryRun | null>(null);
  let errors = $state<string[]>([]);
  let busy = $state(false);

  $effect(() => {
    api.dryRun(type, id).then((r) => (plan = r), (e) => (errors = messagesOf(e)));
  });

  async function confirm() {
    busy = true;
    errors = [];
    try {
      await change(() => api.remove(type, id), `Deleted ${TYPE_LABEL[type].toLowerCase()} “${name}”.`);
      closePanel();
    } catch (e) {
      errors = messagesOf(e);
    } finally {
      busy = false;
    }
  }
</script>

<div class="form">
  <h3>Delete {TYPE_LABEL[type].toLowerCase()} “{name}”?</h3>
  {#if !plan && !errors.length}
    <p class="muted">Checking…</p>
  {:else if plan && plan.blockers.length}
    <p>This cannot be deleted while:</p>
    <ul class="blockers">
      {#each plan.blockers as b}
        <li><EntityLink type={b.type as EntityType} id={b.id} /> <span class="muted">{b.reason}</span></li>
      {/each}
    </ul>
  {:else if plan}
    <p>This will remove:</p>
    <ul>
      {#each plan.removes as r}
        <li><span class="muted">{TYPE_LABEL[r.type as EntityType]}</span> {entityName(ws, r.type as EntityType, r.id)}</li>
      {/each}
    </ul>
  {/if}
  {#if errors.length}
    <ul class="errors" role="alert">{#each errors as err}<li>{err}</li>{/each}</ul>
  {/if}
  <div class="actions">
    <button class="danger" disabled={busy || !plan || plan.blockers.length > 0} onclick={confirm}>Delete</button>
    <button onclick={() => select(type, id)}>Cancel</button>
  </div>
</div>
