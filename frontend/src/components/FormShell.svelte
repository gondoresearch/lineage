<script lang="ts">
  // Common frame for side-panel forms: title, fields, API errors, buttons.
  import type { Snippet } from 'svelte';
  import { closePanel } from '../state.svelte';

  let {
    title,
    errors = [],
    busy = false,
    submitLabel = 'Save',
    onsubmit,
    oncancel = closePanel,
    children,
  }: {
    title: string;
    errors?: string[];
    busy?: boolean;
    submitLabel?: string;
    onsubmit: () => void;
    oncancel?: () => void;
    children: Snippet;
  } = $props();
</script>

<form
  class="form"
  onsubmit={(e) => {
    e.preventDefault();
    onsubmit();
  }}
>
  <h3>{title}</h3>
  {@render children()}
  {#if errors.length}
    <ul class="errors" role="alert">
      {#each errors as err}<li>{err}</li>{/each}
    </ul>
  {/if}
  <div class="actions">
    <button type="submit" class="primary" disabled={busy}>{submitLabel}</button>
    <button type="button" onclick={oncancel}>Cancel</button>
  </div>
</form>
