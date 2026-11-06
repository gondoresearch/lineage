<script lang="ts">
  import type { Schemas } from '../api/client';

  let { links = $bindable([]) }: { links?: Schemas['Link'][] } = $props();
</script>

<div class="links">
  {#each links as link, i}
    <div class="link-row">
      <input placeholder="label" bind:value={link.label} />
      <input placeholder="https://…" bind:value={link.url} />
      <button type="button" aria-label="Remove link" onclick={() => links.splice(i, 1)}>×</button>
    </div>
  {/each}
  <button type="button" onclick={() => links.push({ label: '', url: '' })}>Add link</button>
</div>

<style>
  .links {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    align-items: flex-start;
  }
  .link-row {
    display: grid;
    grid-template-columns: 1fr 2fr auto;
    gap: 0.3rem;
    width: 100%;
  }
</style>
