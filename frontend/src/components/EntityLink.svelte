<script lang="ts">
  import type { EntityType } from '../api/client';
  import { entityName } from '../lib/entities';
  import { app, select } from '../state.svelte';

  let { type, id, label }: { type: EntityType; id: string; label?: string } = $props();
</script>

<button type="button" class="link" onclick={() => select(type, id)}>{label ?? entityName(app.ws!, type, id)}</button>
