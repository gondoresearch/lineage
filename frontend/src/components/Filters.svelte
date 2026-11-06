<script lang="ts">
  // Filter bar: groups, current states, hide inactive. Empty selection = all.
  import { isFiltered } from '../layout/filters';
  import { app } from '../state.svelte';

  const ws = $derived(app.ws!);
  const f = app.filters;

  function toggle(list: string[], id: string) {
    const i = list.indexOf(id);
    if (i >= 0) list.splice(i, 1);
    else list.push(id);
  }
</script>

<div class="filters" aria-label="Filters">
  <span class="label">Groups</span>
  {#each ws.groups as g}
    <button class="chip" class:on={f.groups.includes(g.id)} onclick={() => toggle(f.groups, g.id)}>
      <span class="sw" style:background={g.color}></span>{g.name}
    </button>
  {/each}
  <span class="label">States</span>
  {#each ws.states as s}
    <button class="chip" class:on={f.states.includes(s.id)} onclick={() => toggle(f.states, s.id)}>{s.name}</button>
  {/each}
  <label class="hide"><input type="checkbox" bind:checked={f.hideInactive} /> Hide inactive</label>
  {#if isFiltered(f)}
    <button class="clear" onclick={() => { f.groups.length = 0; f.states.length = 0; f.hideInactive = false; }}>Clear filters</button>
  {/if}
</div>

<style>
  .filters {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.3rem;
    padding: 0.45rem 1rem;
    border-bottom: 1px solid var(--line);
    font-size: 12.5px;
  }
  .label {
    margin: 0 0.2rem 0 0.6rem;
    color: var(--muted);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .label:first-child {
    margin-left: 0;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.1rem 0.55rem;
    border-radius: 999px;
    font-size: 12.5px;
  }
  .chip.on {
    background: var(--fg);
    border-color: var(--fg);
    color: var(--bg);
  }
  .sw {
    width: 9px;
    height: 9px;
    border-radius: 2px;
  }
  .hide {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    margin-left: 0.8rem;
  }
  .clear {
    margin-left: 0.4rem;
    padding: 0.1rem 0.55rem;
    font-size: 12.5px;
  }
</style>
