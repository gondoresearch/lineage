<script lang="ts">
  // Legend generated from the vocabulary (and the groups, for their colours).
  import type { Workspace } from '../api/client';
  import { NEUTRAL } from '../layout/colors';
  import LineSample from './LineSample.svelte';
  import MarkerIcon from './MarkerIcon.svelte';
  import { MARKER_NEUTRAL } from '../layout/colors';
  import { FADED_OPACITY } from './lines';
  import NodeShape from './NodeShape.svelte';

  let { ws }: { ws: Workspace } = $props();
  const WAIT = { me: 'on me', others: 'on others', nobody: 'inactive' } as const;
</script>


<section class="legend">
  <div>
    <h4>Groups</h4>
    {#each ws.groups as g}
      <div class="item"><span class="swatch" style:background={g.color}></span>{g.name}</div>
    {/each}
  </div>
  <div>
    <h4>Kinds</h4>
    {#each ws.kinds as k}
      <div class="item">
        <svg width="16" height="16" aria-hidden="true"><NodeShape shape={k.shape} x={8} y={8} r={Math.min(7.5, 6 * (k.size ?? 1))} color={k.color ?? NEUTRAL} /></svg>
        {k.name}
      </div>
    {/each}
  </div>
  <div>
    <h4>States</h4>
    {#each ws.states as s}
      <div class="item"><LineSample line={s.line} color={s.color ?? NEUTRAL} opacity={s.opacity} thickness={s.line_width} />{s.name} <span class="muted">· {WAIT[s.waiting_on]}</span></div>
    {/each}
  </div>
  <div>
    <h4>References</h4>
    {#each ws.reftypes as r}
      <div class="item"><LineSample line={r.line} color={r.color ?? NEUTRAL} arrow={r.directed} opacity={r.opacity} thickness={r.line_width} />{r.name}</div>
    {/each}
    <h4>History</h4>
    <div class="item"><LineSample line="solid" color={ws.settings.fork_color ?? NEUTRAL} thickness={ws.settings.fork_width} />fork{#if !ws.settings.fork_color}<span class="muted">&nbsp;(project colour)</span>{/if}</div>
    <div class="item"><LineSample line="solid" color={ws.settings.merge_color ?? NEUTRAL} thickness={ws.settings.merge_width} />merge{#if !ws.settings.merge_color}<span class="muted">&nbsp;(project colour)</span>{/if}</div>
  </div>
  <div>
    <h4>Markers</h4>
    <div class="item">
      <svg width="16" height="16" aria-hidden="true" opacity={FADED_OPACITY}><NodeShape shape="open-circle" x={8} y={8} r={6} color={NEUTRAL} /></svg>
      planned
    </div>
    <div class="item">
      <svg width="16" height="16" aria-hidden="true">
        <g opacity={FADED_OPACITY}><NodeShape shape="open-circle" x={7} y={9} r={6} color={NEUTRAL} /></g>
        <circle cx="12.5" cy="3.5" r="3" fill="var(--danger)" />
      </svg>
      overdue
    </div>
    {#each ws.markers ?? [] as mk}
      <div class="item">
        <svg width="16" height="16" aria-hidden="true"><MarkerIcon icon={mk.icon} x={8} y={8} size={12} color={mk.color ?? MARKER_NEUTRAL} /></svg>
        {mk.name}
      </div>
    {/each}
    <div class="item">
      <svg width="40" height="12" aria-hidden="true"><line x1="20" y1="0" x2="20" y2="12" stroke="var(--today)" stroke-width="1.5" /></svg>
      today
    </div>
  </div>
</section>

<style>
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 2.5rem;
    margin-top: 1rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--line);
    font-size: 12.5px;
  }
  h4 {
    margin: 0 0 0.3rem;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
  }
  h4:not(:first-child) {
    margin-top: 0.6rem;
  }
  .item {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    min-height: 20px;
  }
  .swatch {
    width: 12px;
    height: 12px;
    border-radius: 3px;
    margin: 0 2px;
  }
</style>
