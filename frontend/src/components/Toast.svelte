<script lang="ts">
  import { app, undoLast } from '../state.svelte';
</script>

{#if app.toast}
  {#key app.toast.seq}
    <div class="toast" role="status">
      <span>{app.toast.message}</span>
      {#if app.toast.undo}<button onclick={undoLast}>Undo</button>{/if}
      <button class="x" aria-label="Dismiss" onclick={() => { app.toast = null; }}>×</button>
    </div>
  {/key}
{/if}

<style>
  .toast {
    position: fixed;
    left: 50%;
    bottom: 1.25rem;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 0.6rem 0.5rem 1rem;
    border-radius: 8px;
    background: var(--fg);
    color: var(--bg);
    box-shadow: 0 6px 20px rgb(0 0 0 / 0.18);
    z-index: 20;
  }
  .toast button {
    background: transparent;
    color: var(--bg);
    border-color: rgb(255 255 255 / 0.4);
  }
  .toast .x {
    border: none;
    font-size: 1.1rem;
    padding: 0 0.3rem;
  }
</style>
