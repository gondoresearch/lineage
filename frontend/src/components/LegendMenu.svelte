<script lang="ts">
  // Drop-down of one legend entry: hide / show it, show only it, show all of its kind.
  let { hidden, onToggle, onOnly, onAll, onClose }: {
    hidden: boolean;
    onToggle: () => void;
    onOnly: () => void;
    onAll: () => void;
    onClose: () => void;
  } = $props();
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && onClose()} onpointerdown={onClose} />

<div class="menu" role="menu" tabindex="-1" onpointerdown={(e) => e.stopPropagation()}>
  <button role="menuitem" onclick={() => { onToggle(); onClose(); }}>{hidden ? 'Show' : 'Hide'}</button>
  <button role="menuitem" onclick={() => { onOnly(); onClose(); }}>Show only this</button>
  <button role="menuitem" onclick={() => { onAll(); onClose(); }}>Show all</button>
</div>

<style>
  .menu {
    position: absolute;
    top: 100%;
    left: 0;
    z-index: 20;
    display: flex;
    flex-direction: column;
    min-width: 8.5rem;
    padding: 0.2rem;
    background: var(--bg);
    border: 1px solid var(--line);
    border-radius: 6px;
    box-shadow: 0 4px 14px rgb(0 0 0 / 0.18);
  }
  .menu button {
    text-align: left;
    border: 0;
    background: none;
    padding: 0.3rem 0.5rem;
    font-size: 12.5px;
    border-radius: 4px;
  }
  .menu button:hover {
    background: var(--line);
  }
</style>
