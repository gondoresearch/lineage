<script lang="ts">
  // The milestones of one project on one day, shown when a collapsed "×n" mark is clicked.
  import { entityName } from '../lib/entities';
  import { colors } from '../layout/colors';
  import { indexWorkspace, when } from '../layout/model';
  import { app, select } from '../state.svelte';
  import NodeShape from './NodeShape.svelte';

  let { ids }: { ids: string[] } = $props();
  const ws = $derived(app.ws!);
  const idx = $derived(indexWorkspace(ws));
  const c = $derived(colors(idx));
  const ms = $derived(ids.map((id) => idx.milestones.get(id)).filter((m) => m !== undefined));
  const first = $derived(ms[0]);
</script>

{#if first}
  <p class="eyebrow">Milestones on {first.at.slice(0, 10)}</p>
  <h3>{entityName(ws, 'projects', first.project)}</h3>
  <ul class="day">
    {#each ms as m (m.id)}
      {@const k = idx.kinds.get(m.kind)}
      <li>
        <button class="row" onclick={() => select('milestones', m.id)}>
          <svg width="22" height="22" viewBox="-11 -11 22 22" aria-hidden="true">
            <NodeShape shape={k?.shape ?? 'open-circle'} x={0} y={0} r={6 * (k?.size ?? 1)} color={c.milestone(m)} />
          </svg>
          <span class="title">{m.title}</span>
          <span class="muted small">{k?.name ?? m.kind}{m.state ? ` · ${idx.states.get(m.state)?.name ?? m.state}` : ''}{m.planned ? ' · planned' : ''}</span>
          <span class="muted small time">{m.at.endsWith('T00:00') ? '' : m.at.slice(11)}</span>
        </button>
      </li>
    {/each}
  </ul>
  <p class="muted small">Click one to open it. Turn off <b>Collapse days</b> above the timeline to see them all on it.</p>
{/if}

<style>
  .eyebrow {
    margin: 0;
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--muted);
  }
  h3 {
    margin: 0.1rem 1.5rem 0.8rem 0;
  }
  .day {
    list-style: none;
    margin: 0 0 0.8rem;
    padding: 0;
    border: 1px solid var(--line);
    border-radius: 8px;
  }
  .day li + li {
    border-top: 1px solid var(--line);
  }
  .row {
    width: 100%;
    display: grid;
    grid-template-columns: 22px 1fr auto;
    grid-template-rows: auto auto;
    column-gap: 0.5rem;
    align-items: center;
    border: none;
    border-radius: 0;
    background: transparent;
    padding: 0.45rem 0.6rem;
    text-align: left;
  }
  .row svg {
    grid-row: span 2;
  }
  .title {
    font-weight: 500;
  }
  .time {
    grid-column: 3;
    grid-row: 1;
  }
  .row:hover {
    background: var(--panel);
  }
</style>
