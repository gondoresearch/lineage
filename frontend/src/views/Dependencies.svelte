<script lang="ts">
  // Projects as nodes; forks, merges and references aggregated to project level.
  // Laid out with dagre, bottom to top: earlier work below the work that builds on it.
  import type { Workspace } from '../api/client';
  import LineSample from '../components/LineSample.svelte';
  import { CAP, DASH } from '../components/lines';
  import { NEUTRAL } from '../layout/colors';
  import { labelOf, layoutDeps } from '../layout/deps';
  import { projectFilter } from '../layout/filters';
  import { relatedProjects } from '../layout/highlight';
  import { indexWorkspace } from '../layout/model';
  import { app, isSelected, select } from '../state.svelte';

  let { ws }: { ws: Workspace } = $props();

  const idx = $derived(indexWorkspace(ws));
  const L = $derived(layoutDeps(idx, projectFilter(ws, app.filters)));
  const hl = $derived(app.hover?.type === 'projects' ? relatedProjects(ws, app.hover.id) : null);
  const lit = (id: string) => !hl || hl.has(id);
  const arrowColors = $derived([...new Set(L.edges.filter((e) => e.arrow).map((e) => e.color))]);
  const markerId = (color: string) => `dep-arrow-${color.replace('#', '')}`;
  const refsFirst = $derived([...L.edges].sort((a, b) => Number(b.kind === 'reference') - Number(a.kind === 'reference')));

  /** Smooth path through dagre's points (quadratic curves through the midpoints). */
  function pathOf(pts: { x: number; y: number }[]): string {
    if (pts.length < 2) return '';
    const r = (v: number) => Math.round(v * 10) / 10;
    let d = `M${r(pts[0].x)},${r(pts[0].y)}`;
    for (let i = 1; i < pts.length - 1; i++) {
      const mx = (pts[i].x + pts[i + 1].x) / 2;
      const my = (pts[i].y + pts[i + 1].y) / 2;
      d += ` Q${r(pts[i].x)},${r(pts[i].y)} ${r(mx)},${r(my)}`;
    }
    const last = pts[pts.length - 1];
    return d + ` L${r(last.x)},${r(last.y)}`;
  }

  const hover = (id: string | null) => {
    app.hover = id ? { type: 'projects', id } : null;
  };
</script>

{#if L.nodes.length === 0}
  <p class="muted">{ws.projects.length ? 'No project matches the filters.' : 'No projects yet.'}</p>
{:else}
  <svg viewBox="0 0 {L.width} {L.height}" style:max-width="{L.width}px" class="deps" role="img" aria-label="Dependencies">
    <defs>
      {#each arrowColors as color}
        <marker id={markerId(color)} viewBox="0 0 10 10" refX="10" refY="5" markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" orient="auto">
          <path d="M0,0 L10,5 L0,10 z" fill={color} />
        </marker>
      {/each}
    </defs>

    {#each refsFirst as e}
      <path d={pathOf(e.points)} fill="none" stroke={e.color} stroke-width={e.width}
        stroke-dasharray={DASH[e.line]} stroke-linecap={CAP[e.line]} opacity={e.opacity}
        class:dim={!(lit(e.from) && lit(e.to))}
        marker-end={e.arrow ? `url(#${markerId(e.color)})` : undefined}>
        <title>{e.kind === 'reference' ? idx.reftypes.get(e.type ?? '')?.name : e.kind}{e.count > 1 ? ` ×${e.count}` : ''}</title>
      </path>
    {/each}

    {#each L.nodes as n (n.id)}
      <g class="node" class:dim={!lit(n.id)} class:selected={isSelected('projects', n.id)}
        role="button" tabindex="0" aria-label={n.title} data-id={n.id}
        onclick={() => select('projects', n.id)} onkeydown={(e) => e.key === 'Enter' && select('projects', n.id)}
        onmouseenter={() => hover(n.id)} onmouseleave={() => hover(null)}>
        <title>{n.title}</title>
        <rect x={n.x - n.width / 2} y={n.y - n.height / 2} width={n.width} height={n.height} rx="7"
          fill={n.color} fill-opacity="0.12" stroke={n.color} stroke-width={isSelected('projects', n.id) ? 3 : 1.6} />
        <text x={n.x} y={n.y} text-anchor="middle" dominant-baseline="central">{labelOf(n.title)}</text>
      </g>
    {/each}
  </svg>

  <div class="legend">
    <span class="item"><LineSample line="solid" color={ws.settings.fork_color ?? NEUTRAL} thickness={ws.settings.fork_width} />fork</span>
    <span class="item"><LineSample line="solid" color={ws.settings.merge_color ?? NEUTRAL} thickness={ws.settings.merge_width} />merge</span>
    {#each ws.reftypes as t}
      <span class="item"><LineSample line={t.line} color={t.color ?? NEUTRAL} arrow={t.directed} opacity={t.opacity} thickness={t.line_width} />{t.name}</span>
    {/each}
    <span class="muted">Earlier work is drawn below the work that forks, merges or builds on it.</span>
  </div>
{/if}

<style>
  .deps {
    display: block;
    width: 100%;
    margin: 0 auto;
  }
  .node {
    cursor: pointer;
    outline: none;
  }
  .node text {
    font-size: 12.5px;
    fill: var(--fg);
    pointer-events: none;
  }
  .node.selected text {
    font-weight: 600;
  }
  .dim {
    opacity: 0.12;
    transition: opacity 0.12s;
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem 1.4rem;
    margin-top: 1rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--line);
    font-size: 12.5px;
  }
  .item {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
  }
</style>
