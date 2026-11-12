<script lang="ts">
  // Fields, rendered description and actions of the selected entity.
  import type { Domain, EntityType, Group, Kind, Marker, Milestone, Project, Reference, RefType, State } from '../api/client';
  import { colors } from '../layout/colors';
  import { indexWorkspace, localToday, when } from '../layout/model';
  import { entityName, findEntity, TYPE_LABEL } from '../lib/entities';
  import { app, openForm } from '../state.svelte';
  import EntityLink from './EntityLink.svelte';
  import Markdown from './Markdown.svelte';
  import MarkerIcon from './MarkerIcon.svelte';

  let { type, id }: { type: EntityType; id: string } = $props();
  const ws = $derived(app.ws!);
  const e = $derived(findEntity(ws, type, id));
  const c = $derived(colors(indexWorkspace(ws)));
  const WAIT = { me: 'me', others: 'others', nobody: 'nobody (inactive)' };
  const PLACE = { left: 'near the source', center: 'middle', right: 'near the target' };

  const edit = () => openForm(type, { id });
  const editDescription = () => {
    app.panel = { kind: 'description', type, id };
  };
  const del = () => {
    app.panel = { kind: 'delete', type, id };
  };
</script>

{#snippet swatch(own: string | null | undefined, resolved: string)}
  <span class="sw" style:background={resolved}></span>
  {#if own}<code>{own}</code>{:else}<span class="muted">inherited</span>{/if}
{/snippet}

{#snippet links(list: { label: string; url: string }[])}
  {#if list.length}
    <dt>Links</dt>
    <dd>{#each list as l, i}{#if i}, {/if}<a href={l.url} target="_blank" rel="noopener noreferrer">{l.label || l.url}</a>{/each}</dd>
  {/if}
{/snippet}

{#if e}
  <div class="view">
    <p class="kicker">{TYPE_LABEL[type]}</p>
    <!-- a milestone's project is listed below, so the heading is just its title -->
    <h3>{type === 'milestones' ? (e as Milestone).title : entityName(ws, type, id)}</h3>


    <dl>
      {#if type === 'milestones'}
        {@const m = e as Milestone}
        {@const forks = ws.projects.filter((p) => p.from === m.id)}
        {@const mergedInto = ws.milestones.filter((x) => x.merges?.includes(m.id))}
        {@const refs = ws.references.filter((r) => r.from === m.id || r.to === m.id)}
        <dt>Project</dt><dd><EntityLink type="projects" id={m.project} /></dd>
        <dt>When</dt><dd>{when(m.at)}{#if m.planned} · planned{#if m.at.slice(0, 10) < localToday()} · <span class="danger-text">overdue</span>{/if}{/if}</dd>
        <dt>Kind</dt><dd><EntityLink type="kinds" id={m.kind} /></dd>
        <dt>State</dt><dd>{#if m.state}<EntityLink type="states" id={m.state} />{:else if ws.kinds.find((k) => k.id === m.kind)?.closes}<span class="muted">none: closes the project</span>{/if}</dd>
        {#if m.markers?.length}
          <dt>Markers</dt>
          <dd>
            {#each m.markers as mk}
              {@const marker = (ws.markers ?? []).find((x) => x.id === mk)}
              {#if marker}
                <div class="marker-row">
                  <svg width="14" height="14" aria-hidden="true"><MarkerIcon icon={marker.icon} x={7} y={7} size={12} color={c.marker(marker)} /></svg>
                  <EntityLink type="markers" id={mk} />
                </div>
              {/if}
            {/each}
          </dd>
        {/if}
        {#if m.line_text}<dt>Line text</dt><dd>“{m.line_text}” <span class="muted">· on the line after it</span></dd>{/if}
        {#if m.labels?.length}<dt>Labels</dt><dd>{m.labels.join(', ')}</dd>{/if}
        {#if m.merges?.length}<dt>Merges</dt><dd>{#each m.merges as s}<div><EntityLink type="milestones" id={s} /></div>{/each}</dd>{/if}
        {#if mergedInto.length}<dt>Merged into</dt><dd>{#each mergedInto as x}<div><EntityLink type="milestones" id={x.id} /></div>{/each}</dd>{/if}
        {#if forks.length}<dt>Forked by</dt><dd>{#each forks as p}<div><EntityLink type="projects" id={p.id} /></div>{/each}</dd>{/if}
        {#if refs.length}<dt>References</dt><dd>{#each refs as r}<div><EntityLink type="references" id={r.id} /></div>{/each}</dd>{/if}
        {@render links(m.links ?? [])}
        <dt>Colour</dt><dd>{@render swatch(m.color, c.milestone(m))}</dd>
      {:else if type === 'projects'}
        {@const p = e as Project}
        {@const d = ws.derived.projects[p.id]}
        <dt>Group</dt><dd><EntityLink type="groups" id={p.group} /></dd>
        {#if p.from}<dt>Forked from</dt><dd><EntityLink type="milestones" id={p.from} /></dd>{/if}
        <dt>Current state</dt><dd>{#if d?.current_state}<EntityLink type="states" id={d.current_state} />{:else if d?.closed}closed{:else}<span class="muted">nothing has happened yet</span>{/if}{#if d?.merged} · merged{/if}</dd>
        <dt>Milestones</dt>
        <dd>
          {#each d?.milestones ?? [] as mid}
            {@const ms = ws.milestones.find((x) => x.id === mid)}
            <div><EntityLink type="milestones" id={mid} label={ms?.title} /> <span class="muted">{when(ms?.at)}{ms?.planned ? ' · planned' : ''}</span></div>
          {/each}
        </dd>
        {@render links(p.links ?? [])}
        <dt>Colour</dt><dd>{@render swatch(p.color, c.project(p))}</dd>
      {:else if type === 'references'}
        {@const r = e as Reference}
        <dt>Type</dt><dd><EntityLink type="reftypes" id={r.type} /></dd>
        <dt>From</dt><dd><EntityLink type="milestones" id={r.from} /></dd>
        <dt>To</dt><dd><EntityLink type="milestones" id={r.to} /></dd>
        <dt>Recorded</dt><dd>{r.created ? when(r.created) : 'unknown'}</dd>
        {#if r.text}<dt>Line text</dt><dd>“{r.text}” <span class="muted">· {PLACE[r.text_align]} · {r.text_position} · {r.text_orientation === 'along' ? 'along the line' : 'horizontal'}</span></dd>{/if}
        <dt>Colour</dt><dd>{@render swatch(r.color, c.reference(r))}</dd>
      {:else if type === 'domains'}
        {@const dm = e as Domain}
        <dt>Colour</dt><dd>{@render swatch(dm.color, dm.color ?? 'var(--bg)')}</dd>
        <dt>Groups</dt><dd>{#each ws.groups.filter((g) => g.domain === dm.id) as g}<div><EntityLink type="groups" id={g.id} /></div>{:else}<span class="muted">none</span>{/each}</dd>
      {:else if type === 'groups'}
        {@const g = e as Group}
        <dt>Domain</dt><dd>{#if g.domain}<EntityLink type="domains" id={g.domain} />{:else}<span class="muted">none</span>{/if}</dd>
        <dt>Colour</dt><dd>{@render swatch(g.color, g.color ?? '')}</dd>
        <dt>Projects</dt><dd>{#each ws.projects.filter((p) => p.group === g.id) as p}<div><EntityLink type="projects" id={p.id} /></div>{:else}<span class="muted">none</span>{/each}</dd>
      {:else if type === 'kinds'}
        {@const k = e as Kind}
        <dt>Shape</dt><dd>{k.shape} · {Math.round((k.size ?? 1) * 100)}%</dd>
        {#if k.closes}<dt>Closes</dt><dd>yes: its milestones have no state and end the lane</dd>{/if}
        <dt>Default state</dt><dd>{#if k.default_state}<EntityLink type="states" id={k.default_state} />{:else}<span class="muted">none</span>{/if}</dd>
        <dt>Colour</dt><dd>{@render swatch(k.color, k.color ?? 'var(--bg)')}</dd>
      {:else if type === 'states'}
        {@const s = e as State}
        <dt>Line</dt><dd>{s.line}</dd>
        <dt>Waiting on</dt><dd>{WAIT[s.waiting_on]}</dd>
        <dt>Thickness</dt><dd>{s.line_width} px · opacity {Math.round((s.opacity ?? 1) * 100)}%</dd>
        {#if s.text}<dt>Line text</dt><dd>“{s.text}” <span class="muted">· {s.text_align} · {s.text_position}</span></dd>{/if}
        <dt>Colour</dt><dd>{@render swatch(s.color, s.color ?? 'var(--bg)')}</dd>
      {:else if type === 'markers'}
        {@const mk = e as Marker}
        <dt>Icon</dt>
        <dd class="marker-row">
          <svg width="16" height="16" aria-hidden="true"><MarkerIcon icon={mk.icon} x={8} y={8} size={14} color={c.marker(mk)} /></svg>{mk.icon}
        </dd>
        <dt>Colour</dt><dd>{@render swatch(mk.color, c.marker(mk))}</dd>
        <dt>Milestones</dt>
        <dd>
          {#each ws.milestones.filter((x) => x.markers?.includes(mk.id)) as x}<div><EntityLink type="milestones" id={x.id} /></div>{:else}<span class="muted">none</span>{/each}
        </dd>
      {:else if type === 'reftypes'}
        {@const t = e as RefType}
        <dt>Directed</dt><dd>{t.directed ? 'yes' : 'no'}</dd>
        <dt>Line</dt><dd>{t.line}</dd>
        <dt>Colour</dt><dd>{@render swatch(t.color, t.color ?? 'var(--bg)')}</dd>
      {/if}
    </dl>

    <div class="description">
      {#if e.description}<Markdown source={e.description} />{:else}<p class="muted">No description.</p>{/if}
    </div>

    <div class="actions wrap">
      <button onclick={edit}>Edit</button>
      <button onclick={editDescription}>Edit description</button>
      {#if type === 'milestones'}
        {@const m = e as Milestone}
        <button onclick={() => openForm('projects', { preset: { from: m.id, group: ws.projects.find((p) => p.id === m.project)?.group, at: m.at }, title: 'Fork from here' })}>Fork from here</button>
        <button onclick={() => openForm('milestones', { preset: { merges: [m.id], at: m.at }, title: 'Merge into…' })}>Merge into…</button>
        <button onclick={() => openForm('references', { preset: { from: m.id } })}>Add reference</button>
      {:else if type === 'projects'}
        <button onclick={() => openForm('milestones', { preset: { project: id } })}>Add milestone</button>
      {/if}
      <button class="danger" onclick={del}>Delete</button>
    </div>
  </div>
{/if}

<style>
  .kicker {
    margin: 0;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
  }
  h3 {
    margin: 0.1rem 0 0.8rem;
  }
  dl {
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 0.35rem 0.9rem;
    margin: 0 0 1rem;
  }
  dt {
    color: var(--muted);
  }
  dd {
    margin: 0;
    min-width: 0;
  }
  .sw {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 3px;
    border: 1px solid var(--line);
    vertical-align: -1px;
    margin-right: 0.3rem;
  }
  .description {
    padding: 0.6rem 0 0.2rem;
    border-top: 1px solid var(--line);
  }
  .marker-row {
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }
  .danger-text {
    color: var(--danger);
  }
</style>
