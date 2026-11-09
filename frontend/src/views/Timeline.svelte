<script lang="ts">
  import { untrack } from 'svelte';
  import { select as d3select } from 'd3-selection';
  import { zoom, zoomIdentity, type ZoomBehavior } from 'd3-zoom';
  import { api, messagesOf, type Workspace } from '../api/client';
  import Legend from '../components/Legend.svelte';
  import { CAP, DASH, FADED_OPACITY } from '../components/lines';
  import MarkerIcon from '../components/MarkerIcon.svelte';
  import NodeShape from '../components/NodeShape.svelte';
  import { colors } from '../layout/colors';
  import { dropSlots, laneSubtree, layoutLanes, moveRequest, nearestSlot } from '../layout/lanes';
  import { projectFilter } from '../layout/filters';
  import { relatedMilestones } from '../layout/highlight';
  import { indexWorkspace, keyAt, localNow, localToday, when } from '../layout/model';
  import { computeTimeline, ranks } from '../layout/timeline';
  import { eventScale, timeScale, type Mode } from '../layout/xscale';
  import { app, change, isSelected, isSelectedLine, select, selectLine, showToast, stopPicking } from '../state.svelte';

  let { ws }: { ws: Workspace } = $props();

  const LABEL_W = 250;
  const AXIS_H = 26;
  const INDENT = 12;
  /** offset of the rule under a domain heading */
  const DOMAIN_RULE = 9;
  /** marker badge size and spacing */
  const BADGE = 10;
  const BADGE_STEP = 11;

  let width = $state(0);
  let svgEl: SVGSVGElement | undefined = $state();
  let plotEl: SVGGElement | undefined = $state();
  let zoomer: ZoomBehavior<SVGGElement, unknown> | undefined;

  /** today (Days) or now (Hours), at the unit the timeline uses */
  const today = $derived(app.timeline.unit === 'hour' ? localNow() : localToday());
  const idx = $derived(indexWorkspace(ws));
  const c = $derived(colors(idx));
  const lanes = $derived(layoutLanes(idx, projectFilter(ws, app.filters)));
  // Hover: highlight related milestones, dim everything else.
  const hl = $derived(app.hover?.type === 'milestones' ? relatedMilestones(ws, app.hover.id) : null);
  const lit = (id: string | null) => !hl || id === null || hl.has(id);
  const litProject = (pid: string) => !hl || (ws.derived.projects[pid]?.milestones ?? []).some((m) => hl.has(m));
  const plotW = $derived(Math.max(100, width - LABEL_W));
  const plotH = $derived(lanes.height);
  const xs = $derived.by(() => {
    const unit = app.timeline.unit;
    const rk = ranks(idx, unit);
    const slots = ws.milestones.map((m) => ({ date: keyAt(m.at, unit), rank: rk.get(m.id) ?? 0 }));
    return app.timeline.mode === 'time' ? timeScale(slots, today, plotW) : eventScale(slots, today, plotW);
  });
  const geo = $derived(computeTimeline(idx, lanes, xs, app.timeline.zoom, today, app.timeline.unit));
  const ticks = $derived(xs.ticks(app.timeline.zoom, plotW));
  const arrowColors = $derived([...new Set(geo.edges.filter((e) => e.arrow).map((e) => e.color))]);
  const titles = $derived(new Map(ws.milestones.map((m) => [m.id, m])));

  // Horizontal pan and zoom; the vertical component of the transform is ignored.
  $effect(() => {
    if (!plotEl) return;
    const sel = d3select(plotEl);
    zoomer = zoom<SVGGElement, unknown>()
      .scaleExtent([0.25, 20_000]) // deep enough to read minutes in the Hours view
      .on('zoom', (e) => {
        app.timeline.zoom = { k: e.transform.k, x: e.transform.x };
      });
    sel.call(zoomer).on('dblclick.zoom', null);
    // Restore the saved zoom without subscribing to it (that would loop:
    // applying the transform fires a zoom event, which writes the zoom).
    const { k, x } = untrack(() => app.timeline.zoom);
    sel.call(zoomer.transform, zoomIdentity.translate(x, 0).scale(k));
    return () => {
      sel.on('.zoom', null);
    };
  });

  function setUnit(u: 'day' | 'hour') {
    app.timeline.unit = u;
  }

  function setMode(mode: Mode) {
    app.timeline.mode = mode;
    resetZoom();
  }

  function resetZoom() {
    if (plotEl && zoomer) d3select(plotEl).call(zoomer.transform, zoomIdentity);
    else app.timeline.zoom = { k: 1, x: 0 };
  }

  /** Approximate half width of an 11px tick label. */
  const halfLabel = (s: string) => s.length * 3.2;
  // ---------------------------------------------------------------- dragging lane labels
  // Press on a label and move more than 4px to drag; release over a slot to move
  // the project there (possibly into another group). A plain click still selects.
  const DRAG_THRESHOLD = 4;
  let drag = $state<{ pid: string; startY: number; y: number; active: boolean } | null>(null);
  let suppressClick = false;
  const slots = $derived(dropSlots(lanes));
  const dropAt = $derived(drag?.active ? nearestSlot(slots, drag.y - AXIS_H) : null);

  const svgY = (e: PointerEvent) => e.clientY - svgEl!.getBoundingClientRect().top;

  function dragStart(e: PointerEvent, pid: string) {
    if (e.button !== 0) return;
    drag = { pid, startY: svgY(e), y: svgY(e), active: false };
  }

  function dragMove(e: PointerEvent) {
    if (!drag) return;
    drag.y = svgY(e);
    if (!drag.active && Math.abs(drag.y - drag.startY) > DRAG_THRESHOLD) {
      drag.active = true;
      // Capture only once dragging: capturing on press would retarget the
      // click of a plain press-and-release away from the label.
      (e.currentTarget as Element).setPointerCapture(e.pointerId);
    }
  }

  async function dragEnd() {
    const d = drag;
    drag = null;
    if (!d?.active) return;
    // The click that follows this pointerup must not select the project.
    suppressClick = true;
    setTimeout(() => (suppressClick = false), 0);
    const slot = nearestSlot(slots, d.y - AXIS_H);
    if (!slot) return;
    const projects = ws.projects.map((p) => ({
      id: p.id,
      group: p.group,
      origin: p.from ? (idx.milestones.get(p.from)?.project ?? null) : null,
    }));
    const req = moveRequest(projects, lanes, d.pid, slot);
    if (!req) return;
    const p = idx.projects.get(d.pid)!;
    let what = `“${p.title}”`;
    if (req.group !== p.group) {
      // Its forks drawn under it move along (done by the backend).
      const n = laneSubtree(projects, d.pid).length;
      if (n) what += ` and ${n} fork${n > 1 ? 's' : ''}`;
      what += ` to ${idx.groups.get(req.group)?.name}`;
    }
    try {
      await change(() => api.update('projects', d.pid, req), `Moved ${what}.`);
    } catch (err) {
      showToast(messagesOf(err).join(' '), false);
    }
  }

  /** Clicking a milestone while a form waits for one hands it to the form. */
  function pickMilestone(id: string) {
    const p = app.picking!;
    if (id === p.exclude) {
      showToast('That is the source milestone; pick another one.', false);
      return;
    }
    // The same click must not also select the milestone (that would close the form).
    suppressClick = true;
    setTimeout(() => (suppressClick = false), 0);
    p.onPick(id);
  }

  /** Click + Enter handlers for SVG elements that select an entity. */
  const pick = (fn: () => void) => ({
    role: 'button',
    tabindex: 0,
    onclick: () => {
      // While picking, only milestones react (see the node handler).
      if (!suppressClick && !app.picking) fn();
    },
    onkeydown: (e: KeyboardEvent) => e.key === 'Enter' && fn(),
  });
  /** Extra indent for everything inside a domain block. */
  const domainIndent = (group: string) => (idx.groups.get(group)?.domain && idx.domains.get(idx.groups.get(group)!.domain!) ? 10 : 0);
  const clip = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1) + '…' : s);
  const markerId = (color: string) => `arrow-${color.replace('#', '')}`;
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && app.picking && stopPicking()} />

{#if app.picking}
  <div class="picking-banner" role="status">
    <span>{app.picking.prompt}</span>
    <button onclick={stopPicking}>Cancel</button>
  </div>
{/if}

<div class="controls">
  <div class="seg" role="group" aria-label="Horizontal axis">
    <button class:on={app.timeline.mode === 'time'} onclick={() => setMode('time')}>Time</button>
    <button class:on={app.timeline.mode === 'event'} onclick={() => setMode('event')}>Event order</button>
  </div>
  <div class="seg" role="group" aria-label="Unit">
    <button class:on={app.timeline.unit === 'day'} onclick={() => setUnit('day')} title="Place milestones by their day">Days</button>
    <button class:on={app.timeline.unit === 'hour'} onclick={() => setUnit('hour')} title="Place milestones at their time of day">Hours</button>
  </div>
  <button onclick={resetZoom}>Reset zoom</button>
  <span class="muted hint">Drag to pan, scroll to zoom.</span>
</div>

<div class="timeline" bind:clientWidth={width}>
  {#if width > 0}
    <svg bind:this={svgEl} {width} height={AXIS_H + plotH + 8} role="img" aria-label="Timeline" class:dragging={drag?.active} class:picking={!!app.picking}>
      <defs>
        <clipPath id="label-clip"><rect x="0" y="0" width={LABEL_W - 10} height={AXIS_H + plotH} /></clipPath>
        <clipPath id="plot-clip"><rect x="0" y={-AXIS_H} width={plotW} height={AXIS_H + plotH + 8} /></clipPath>
        {#each arrowColors as color}
          <marker id={markerId(color)} viewBox="0 0 10 10" refX="10" refY="5" markerUnits="userSpaceOnUse"
            markerWidth="9" markerHeight="9" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill={color} />
          </marker>
        {/each}
      </defs>

      <!-- group bands -->
      {#each lanes.bands as b}
        {@const g = idx.groups.get(b.group)}
        <rect x="0" y={AXIS_H + b.y0} {width} height={b.y1 - b.y0} fill={g?.color} fill-opacity="0.06" />
        <rect x="0" y={AXIS_H + b.y0} width="4" height={b.y1 - b.y0} fill={g?.color}><title>{g?.name}</title></rect>
      {/each}

      <g bind:this={plotEl} transform="translate({LABEL_W},{AXIS_H})" class="plot">
        <rect x="0" y={-AXIS_H} width={plotW} height={AXIS_H + plotH + 8} fill="transparent" />
        <g clip-path="url(#plot-clip)">
          {#each ticks as t}
            <line x1={t.x} x2={t.x} y1="0" y2={plotH} stroke="var(--line)" />
            <!-- label hidden where it would be cut at an edge or collide with "today" -->
            {#if t.x - halfLabel(t.label) > 0 && t.x + halfLabel(t.label) < plotW && Math.abs(t.x - geo.todayX - 18) > halfLabel(t.label) + 24}
              <text x={t.x} y="-9" text-anchor="middle" class="tick">{t.label}</text>
            {/if}
          {/each}

          <line x1={geo.todayX} x2={geo.todayX} y1="-4" y2={plotH} stroke="var(--today)" stroke-width="1.5" />
          <text x={geo.todayX + 4} y="-9" class="today">{app.timeline.unit === 'hour' ? 'now' : 'today'}</text>

          <!-- references first, so they never cover lanes, forks, merges or symbols -->
          {#each geo.edges.filter((e) => e.kind === 'reference') as e}
            {@const sel = isSelected('references', e.id)}
            <path d={e.path} fill="none" stroke={e.color} stroke-width={sel ? e.width + 1.2 : e.width} class:dim={!(lit(e.from) && lit(e.to))}
              stroke-dasharray={DASH[e.line]} stroke-linecap={CAP[e.line]} opacity={sel ? 1 : e.opacity}
              marker-end={e.arrow ? `url(#${markerId(e.color)})` : undefined} />
          {/each}

          {#each geo.segments as s}
            <line x1={s.x1} x2={s.x2} y1={s.y} y2={s.y} stroke={s.color} stroke-width={s.width} class:dim={!(lit(s.from) && lit(s.to))}
              stroke-dasharray={DASH[s.line]} stroke-linecap={CAP[s.line]}
              opacity={s.opacity * (s.faded ? FADED_OPACITY : 1)} />
          {/each}

          {#each geo.edges.filter((e) => e.kind !== 'reference') as e}
            <path d={e.path} fill="none" stroke={e.color} stroke-width={e.width} opacity={e.opacity} class:dim={!(lit(e.from) && lit(e.to))} />
          {/each}

          <!-- optional line text (states and individual references), with a halo so it stays readable -->
          {#each geo.segments.filter((x) => x.label) as s}
            {@const t = s.label!}
            <text x={t.x} y={t.y} text-anchor={t.anchor} dominant-baseline={t.baseline} class="line-text" fill={s.color} font-size={t.size}
              opacity={s.opacity * (s.faded ? FADED_OPACITY : 1)} class:dim={!(lit(s.from) && lit(s.to))}>{t.text}</text>
          {/each}
          {#each geo.edges.filter((x) => x.label) as e}
            {@const t = e.label!}
            <text x={t.x} y={t.y} text-anchor={t.anchor} dominant-baseline={t.baseline} class="line-text" fill={e.color} font-size={t.size}
              transform={t.angle ? `rotate(${t.angle} ${t.x} ${t.y})` : undefined}
              class:dim={!(lit(e.from) && lit(e.to))}>{t.text}</text>
          {/each}

          <!-- lane lines: click to open that line (its text, its milestone's state); the line being edited is highlighted -->
          {#each geo.segments as s}
            {@const st = titles.get(s.from)?.state}
            {#if st}
              {#if isSelectedLine(st, s.from)}
                <line x1={s.x1} x2={s.x2} y1={s.y} y2={s.y} stroke="var(--accent)" stroke-width={s.width + 5} opacity="0.25" class="sel-line" />
              {/if}
              <line x1={s.x1} x2={s.x2} y1={s.y} y2={s.y} stroke="transparent" stroke-width={Math.max(10, s.width + 6)} class="hit"
                {...pick(() => selectLine(s.from))} aria-label="State line" data-from={s.from}><title>{ws.states.find((x) => x.id === st)?.name}</title></line>
            {/if}
          {/each}

          <!-- wide invisible hit areas so thin reference lines can be clicked -->
          {#each geo.edges.filter((e) => e.kind === 'reference') as e}
            <path d={e.path} fill="none" stroke="transparent" stroke-width="10" class="hit"
              {...pick(() => select('references', e.id))} aria-label="Reference" data-id={e.id}><title>{ws.reftypes.find((t) => t.id === ws.references.find((r) => r.id === e.id)?.type)?.name}</title></path>
          {/each}

          {#each geo.nodes as n (n.id)}
            {#if isSelected('milestones', n.id)}
              <circle cx={n.x} cy={n.y} r={n.r + 4.5} fill="none" stroke="var(--accent)" stroke-width="2" class="ring" />
            {/if}
            {@const m = titles.get(n.id)}
            <g class="node" class:dim={!lit(n.id)} opacity={n.planned ? FADED_OPACITY : 1}
              onmouseenter={() => {
                app.hover = { type: 'milestones', id: n.id };
              }}
              onmouseleave={() => {
                app.hover = null;
              }} {...pick(() => select('milestones', n.id))} onclickcapture={(e: MouseEvent) => {
                if (app.picking) {
                  e.stopPropagation();
                  pickMilestone(n.id);
                }
              }} aria-label={m?.title} data-id={n.id}>
              <title>{m?.title} · {when(m?.at)}{n.planned ? (n.overdue ? ' · planned, overdue' : ' · planned') : ''}</title>
              <NodeShape shape={n.shape} x={n.x} y={n.y} r={n.r} color={n.color} />
              <circle cx={n.x} cy={n.y} r={n.r + 3} fill="transparent" />
            </g>
            {#if n.overdue || n.markers.length}
              <!-- badges in a row at the upper right: overdue dot, then user markers (not faded with planned nodes) -->
              {@const bx = n.x + n.r * 0.7 + 2}
              <!-- capped so badges of large symbols stay inside the lane -->
              {@const by = n.y - Math.min(n.r * 0.7 + 4, 11)}
              <g class="badges" class:dim={!lit(n.id)} {...pick(() => select('milestones', n.id))}>
                {#if n.overdue}
                  <circle cx={bx + 3} cy={by} r="3" fill="var(--danger)"><title>overdue</title></circle>
                {/if}
                {#each n.markers as mk, i}
                  <g>
                    <title>{mk.name}</title>
                    <MarkerIcon icon={mk.icon} x={bx + (n.overdue ? 8 : 0) + 5 + i * BADGE_STEP} y={by} size={BADGE} color={mk.color} />
                  </g>
                {/each}
              </g>
            {/if}
          {/each}
        </g>
      </g>

      <!-- fixed label column (drawn last so it covers anything panned under it) -->
      <rect x="4" y="0" width={LABEL_W - 4} height={AXIS_H} fill="var(--bg)" />
      <g clip-path="url(#label-clip)">
      <!-- domain and group headings -->
      {#each lanes.headers as h}
        {#if h.kind === 'domain'}
          {@const d = idx.domains.get(h.id)}
          <g class="heading" {...pick(() => select('domains', h.id))} data-domain={h.id}>
            <!-- text in the normal text colour (readable in both themes); the domain colour marks it -->
            <rect x="12" y={h.y + AXIS_H - 5} width="4" height="12" rx="1" fill={d?.color ?? 'var(--muted)'} />
            <text x="21" y={h.y + AXIS_H + 1} dominant-baseline="central" class="domain-head"
              class:selected={isSelected('domains', h.id)}>{clip((d?.name ?? h.id).toUpperCase(), 26)}</text>
            <line x1="12" x2={LABEL_W - 12} y1={h.y + AXIS_H + DOMAIN_RULE} y2={h.y + AXIS_H + DOMAIN_RULE} stroke={d?.color ?? 'var(--line)'} stroke-width="1.5" />
          </g>
        {:else}
          {@const g = idx.groups.get(h.id)}
          {@const dx = domainIndent(h.id)}
          <g class="heading" {...pick(() => select('groups', h.id))} data-group={h.id}>
            <rect x={12 + dx} y={h.y + AXIS_H - 4.5} width="9" height="9" rx="2" fill={g?.color} />
            <text x={26 + dx} y={h.y + AXIS_H} dominant-baseline="central" class="group-head"
              class:selected={isSelected('groups', h.id)}>{clip(g?.name ?? h.id, Math.floor((LABEL_W - 40 - dx) / 7.4))}</text>
          </g>
        {/if}
      {/each}
      {#each lanes.lanes as l}
        {@const p = idx.projects.get(l.project)}
        {@const dx = domainIndent(l.group) + 12}
        {#if p}
          <g class="lane-label" class:lifted={drag?.active && drag.pid === p.id} class:dim={!litProject(p.id)}
            onpointerdown={(e) => dragStart(e, p.id)} onpointermove={dragMove} onpointerup={dragEnd}
            onpointercancel={() => (drag = null)} role="presentation">
            <rect x="4" y={l.y + AXIS_H - 17} width={LABEL_W - 8} height="34" fill="transparent" />
            <rect x={10 + dx + l.depth * INDENT} y={l.y + AXIS_H - 4} width="8" height="8" rx="2" fill={c.project(p)} />
            <text x={22 + dx + l.depth * INDENT} y={l.y + AXIS_H} dominant-baseline="central" class="label"
              class:selected={isSelected('projects', p.id)} {...pick(() => select('projects', p.id))} data-id={p.id}>
              <title>{p.title} (drag to move)</title>{clip(p.title, Math.floor((LABEL_W - 30 - dx - l.depth * INDENT) / 7.2))}
            </text>
          </g>
        {/if}
      {/each}
      </g>
      {#if drag?.active && dropAt}
        {@const p = idx.projects.get(drag.pid)}
        <line x1="4" x2={width} y1={AXIS_H + dropAt.y} y2={AXIS_H + dropAt.y} stroke="var(--accent)" stroke-width="2" />
        <circle cx="6" cy={AXIS_H + dropAt.y} r="3.5" fill="var(--accent)" />
        {@const t = clip(p?.title ?? '', 30)}
        <rect x="16" y={drag.y - 11} width={t.length * 7.4 + 14} height="22" rx="5" fill="var(--bg)" stroke="var(--accent)"
          stroke-width="1.5" class="floating" />
        <text x="23" y={drag.y} dominant-baseline="central" class="label floating">{t}</text>
      {/if}
      <line x1={LABEL_W - 0.5} x2={LABEL_W - 0.5} y1="0" y2={AXIS_H + plotH} stroke="var(--line)" />
    </svg>
  {/if}
</div>

{#if ws.projects.length === 0}
  <p class="muted">No projects yet.</p>
{:else if lanes.lanes.length === 0}
  <p class="muted">No project matches the filters.</p>
{/if}

<Legend {ws} />

<style>
  .controls {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.6rem;
  }
  .hint {
    font-size: 12px;
  }
  .timeline {
    width: 100%;
    min-height: 40px;
  }
  svg {
    display: block;
    user-select: none;
  }
  .plot {
    cursor: grab;
  }
  .plot:active {
    cursor: grabbing;
  }
  .tick {
    font-size: 11px;
    fill: var(--muted);
  }
  .today {
    font-size: 11px;
    fill: var(--today);
  }
  .label {
    font-size: 13px;
    fill: var(--fg);
    cursor: pointer;
  }
  .heading {
    cursor: pointer;
    outline: none;
  }
  .domain-head {
    fill: var(--fg);
    font-size: 11.5px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }
  .group-head {
    font-size: 12.5px;
    font-weight: 600;
    fill: var(--fg);
  }
  .heading:hover text,
  .domain-head.selected,
  .group-head.selected {
    text-decoration: underline;
  }
  .label:hover,
  .label.selected {
    fill: var(--accent);
  }
  .label.selected {
    font-weight: 600;
  }
  .picking-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.6rem;
    padding: 0.45rem 0.5rem 0.45rem 0.8rem;
    border: 1.5px dashed var(--accent);
    border-radius: 8px;
    background: var(--accent-bg);
    color: var(--accent);
    font-weight: 500;
  }
  svg.picking .node {
    cursor: crosshair;
  }
  svg.picking .node:hover {
    filter: drop-shadow(0 0 3px var(--accent));
  }
  svg.picking .lane-label,
  svg.picking .hit {
    cursor: default;
  }
  /* hover highlighting: CSS opacity overrides the opacity attributes */
  .dim {
    opacity: 0.12;
    transition: opacity 0.12s;
  }
  .lane-label {
    cursor: grab;
    touch-action: none;
  }
  .lane-label.lifted {
    opacity: 0.35;
  }
  svg.dragging,
  svg.dragging * {
    cursor: grabbing !important;
  }
  .floating {
    pointer-events: none;
  }
  .label.floating {
    fill: var(--accent);
    font-weight: 600;
  }
  /* focus ring for keyboard users only, not after a mouse press or drag */
  .label:focus {
    outline: none;
  }
  .label:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .line-text {
    font-weight: 500;
    stroke: var(--bg);
    stroke-width: 3.5px;
    stroke-linejoin: round;
    paint-order: stroke;
    pointer-events: none;
  }
  .sel-line,
  .ring {
    pointer-events: none;
  }
  .badges {
    cursor: pointer;
    outline: none;
  }
  .node,
  .hit {
    cursor: pointer;
    outline: none;
  }
</style>
