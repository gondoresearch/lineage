<script lang="ts">
  // Plain textarea with a Preview toggle (Markdown + $…$ / $$…$$ math).
  import Markdown from './Markdown.svelte';

  let { value = $bindable('') }: { value?: string } = $props();
  let preview = $state(false);
</script>

<div class="desc">
  <div class="seg small" role="group" aria-label="Description mode">
    <button type="button" class:on={!preview} onclick={() => (preview = false)}>Write</button>
    <button type="button" class:on={preview} onclick={() => (preview = true)}>Preview</button>
  </div>
  {#if preview}
    <div class="preview">
      {#if value.trim()}<Markdown source={value} />{:else}<span class="muted">Nothing to preview.</span>{/if}
    </div>
  {:else}
    <textarea bind:value rows="9" placeholder="Markdown; math with $…$ and $$…$$"></textarea>
  {/if}
</div>

<style>
  .desc {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }
  .preview {
    min-height: 8rem;
    padding: 0.4rem 0.6rem;
    border: 1px solid var(--line);
    border-radius: 6px;
  }
</style>
