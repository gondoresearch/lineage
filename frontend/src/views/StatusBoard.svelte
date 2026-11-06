<script lang="ts">
  import type { Workspace } from '../api/client';
  import LineSample from '../components/LineSample.svelte';
  import { colors, NEUTRAL } from '../layout/colors';
  import { projectFilter } from '../layout/filters';
  import { relatedProjects } from '../layout/highlight';
  import { indexWorkspace, localToday } from '../layout/model';
  import { formatDays, statusBoard, type Column } from '../layout/status';
  import { app, isSelected, select } from '../state.svelte';

  let { ws }: { ws: Workspace } = $props();

  const COLUMNS: { id: Column; title: string }[] = [
    { id: 'me', title: 'On me' },
    { id: 'others', title: 'On others' },
    { id: 'inactive', title: 'Inactive' },
  ];
  const idx = $derived(indexWorkspace(ws));
  const c = $derived(colors(idx));
  const board = $derived(statusBoard(ws, localToday(), projectFilter(ws, app.filters)));
  const hl = $derived(app.hover?.type === 'projects' ? relatedProjects(ws, app.hover.id) : null);

  const hover = (id: string | null) => {
    app.hover = id ? { type: 'projects', id } : null;
  };
</script>

<div class="board">
  {#each COLUMNS as col}
    <section>
      <h2>{col.title} <span class="muted">{board[col.id].length}</span></h2>
      {#each board[col.id] as card (card.project)}
        {@const p = idx.projects.get(card.project)!}
        {@const st = card.state ? idx.states.get(card.state) : undefined}
        {@const head = card.head ? idx.milestones.get(card.head) : undefined}
        {@const next = card.next ? idx.milestones.get(card.next) : undefined}
        <button class="card" class:selected={isSelected('projects', p.id)} class:dim={hl && !hl.has(p.id)}
          style:--c={c.project(p)} onclick={() => select('projects', p.id)}
          onmouseenter={() => hover(p.id)} onmouseleave={() => hover(null)} data-id={p.id}>
          <div class="title">{p.title}</div>
          <div class="group muted">{idx.groups.get(p.group)?.name}</div>
          <div class="state">
            {#if st}
              <LineSample line={st.line} color={st.color ?? NEUTRAL} opacity={st.opacity} width={28} />
              <span>{st.name}</span>
              <span class="muted">· {card.days !== null ? formatDays(card.days) : ''}</span>
            {:else}
              <span class="muted">no head yet</span>
            {/if}
          </div>
          {#if head}<div class="row"><span class="muted">Head</span> {head.title} <span class="muted">{head.date}</span></div>{/if}
          {#if next}
            <div class="row" class:overdue={card.nextOverdue}>
              <span class="muted">Next</span> {next.title} <span class:muted={!card.nextOverdue}>{next.date}{card.nextOverdue ? ' · overdue' : ''}</span>
            </div>
          {/if}
        </button>
      {:else}
        <p class="muted empty">Nothing here.</p>
      {/each}
    </section>
  {/each}
</div>

<style>
  .board {
    display: grid;
    grid-template-columns: repeat(3, minmax(220px, 1fr));
    gap: 1.25rem;
    align-items: start;
  }
  h2 {
    margin: 0 0 0.6rem;
    font-size: 14px;
  }
  section {
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
  }
  .card {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    width: 100%;
    padding: 0.55rem 0.7rem 0.6rem 0.85rem;
    border: 1px solid var(--line);
    border-left: 4px solid var(--c);
    border-radius: 8px;
    background: var(--bg);
    text-align: left;
    transition: opacity 0.12s;
  }
  .card:hover {
    border-color: var(--muted);
    border-left-color: var(--c);
  }
  .card.selected {
    box-shadow: 0 0 0 2px var(--accent);
  }
  .card.dim {
    opacity: 0.25;
  }
  .title {
    font-weight: 600;
  }
  .group {
    font-size: 12px;
    margin-top: -0.15rem;
  }
  .state {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    margin-top: 0.15rem;
  }
  .row {
    font-size: 12.5px;
  }
  .row .muted:first-child {
    display: inline-block;
    width: 2.6rem;
  }
  .overdue {
    color: var(--danger);
  }
  .empty {
    margin: 0;
    font-size: 12.5px;
  }
</style>
