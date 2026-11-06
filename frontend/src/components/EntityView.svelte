<script lang="ts">
  // Fields, rendered description and actions of the selected entity.
  import type { EntityType, Group, Kind, Marker, Milestone, Project, Reference, RefType, State } from '../api/client';
  import { colors } from '../layout/colors';
  import { indexWorkspace, localToday } from '../layout/model';
  import { entityName, findEntity, TYPE_LABEL } from '../lib/entities';
  import { untrack } from 'svelte';
  import { api, messagesOf } from '../api/client';
  import { app, change, openForm, selectStateLine } from '../state.svelte';
  import EntityLink from './EntityLink.svelte';
  import LineTextFields from './LineTextFields.svelte';
  import Markdown from './Markdown.svelte';
  import MarkerIcon from './MarkerIcon.svelte';

  let { type, id, via }: { type: EntityType; id: string; via?: string } = $props();
  const ws = $derived(app.ws!);
  let viaErrors = $state<string[]>([]);
  // Text for just the clicked line: stored on the milestone the line follows.
  const viaMs = untrack(() => (via ? ws.milestones.find((m) => m.id === via) : undefined));
  let lt = $state({
    line_text: viaMs?.line_text ?? '',
    line_text_align: viaMs?.line_text_align ?? ('center' as 'left' | 'center' | 'right'),
    line_text_position: viaMs?.line_text_position ?? ('above' as 'above' | 'middle' | 'below'),
    line_text_size: viaMs?.line_text_size ?? 10,
  });

  async function saveLineText() {
    if (!via) return;
    viaErrors = [];
    try {
      await change(() => api.update('milestones', via, { ...lt }), `Saved the text of the line after “${entityName(ws, 'milestones', via)}”.`);
    } catch (e) {
      viaErrors = messagesOf(e);
    }
  }

  /** Change the state of the milestone whose line was clicked (the line now shows that state). */
  async function setViaState(stateId: string) {
    if (!via) return;
    viaErrors = [];
    try {
      await change(() => api.update('milestones', via, { state: stateId }), `Changed the state after “${entityName(ws, 'milestones', via)}”.`);
      selectStateLine(stateId, via);
    } catch (e) {
      viaErrors = messagesOf(e);
    }
  }
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
    <h3>{entityName(ws, type, id)}</h3>

    {#if type === 'states' && via}
      <div class="via">
        <div>The line you clicked follows <EntityLink type="milestones" id={via} />.</div>
        <div class="line-text-form">
          <LineTextFields bind:text={lt.line_text} bind:align={lt.line_text_align} bind:position={lt.line_text_position}
            bind:size={lt.line_text_size} label="Text on this line" />
          <div><button class="primary" onclick={saveLineText}>Save line text</button></div>
        </div>
        <label>Change that milestone's state
          <select value={id} onchange={(e) => setViaState(e.currentTarget.value)}>
            {#each ws.states as s}<option value={s.id}>{s.name}</option>{/each}
          </select>
        </label>
        {#if viaErrors.length}<ul class="errors">{#each viaErrors as err}<li>{err}</li>{/each}</ul>{/if}
        <div class="muted small">Edit below changes how <em>every</em> “{entityName(ws, 'states', id)}” line looks, including its default text.</div>
      </div>
    {/if}

    <dl>
      {#if type === 'milestones'}
        {@const m = e as Milestone}
        {@const forks = ws.projects.filter((p) => p.from === m.id)}
        {@const mergedInto = ws.milestones.filter((x) => x.merges?.includes(m.id))}
        {@const refs = ws.references.filter((r) => r.from === m.id || r.to === m.id)}
        <dt>Project</dt><dd><EntityLink type="projects" id={m.project} /></dd>
        <dt>Date</dt><dd>{m.date}{#if m.planned} · planned{#if m.date < localToday()} · <span class="danger-text">overdue</span>{/if}{/if}</dd>
        <dt>Kind</dt><dd><EntityLink type="kinds" id={m.kind} /></dd>
        <dt>State</dt><dd>{#if m.state}<EntityLink type="states" id={m.state} />{/if}</dd>
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
        <dt>Current state</dt><dd>{#if d?.current_state}<EntityLink type="states" id={d.current_state} />{:else}<span class="muted">no head yet</span>{/if}{#if d?.merged} · merged{/if}</dd>
        <dt>Milestones</dt>
        <dd>
          {#each d?.milestones ?? [] as mid}
            {@const ms = ws.milestones.find((x) => x.id === mid)}
            <div><EntityLink type="milestones" id={mid} label={ms?.title} /> <span class="muted">{ms?.date}{ms?.planned ? ' · planned' : ''}</span></div>
          {/each}
        </dd>
        {@render links(p.links ?? [])}
        <dt>Colour</dt><dd>{@render swatch(p.color, c.project(p))}</dd>
      {:else if type === 'references'}
        {@const r = e as Reference}
        <dt>Type</dt><dd><EntityLink type="reftypes" id={r.type} /></dd>
        <dt>From</dt><dd><EntityLink type="milestones" id={r.from} /></dd>
        <dt>To</dt><dd><EntityLink type="milestones" id={r.to} /></dd>
        {#if r.text}<dt>Line text</dt><dd>“{r.text}” <span class="muted">· {PLACE[r.text_align]} · {r.text_position} · {r.text_orientation === 'along' ? 'along the line' : 'horizontal'}</span></dd>{/if}
        <dt>Colour</dt><dd>{@render swatch(r.color, c.reference(r))}</dd>
      {:else if type === 'groups'}
        {@const g = e as Group}
        <dt>Colour</dt><dd>{@render swatch(g.color, g.color ?? '')}</dd>
        <dt>Projects</dt><dd>{#each ws.projects.filter((p) => p.group === g.id) as p}<div><EntityLink type="projects" id={p.id} /></div>{:else}<span class="muted">none</span>{/each}</dd>
      {:else if type === 'kinds'}
        {@const k = e as Kind}
        <dt>Shape</dt><dd>{k.shape} · {Math.round((k.size ?? 1) * 100)}%</dd>
        <dt>Default state</dt><dd>{#if k.default_state}<EntityLink type="states" id={k.default_state} />{:else}<span class="muted">none</span>{/if}</dd>
        <dt>Colour</dt><dd>{@render swatch(k.color, k.color ?? '#ffffff')}</dd>
      {:else if type === 'states'}
        {@const s = e as State}
        <dt>Line</dt><dd>{s.line}</dd>
        <dt>Waiting on</dt><dd>{WAIT[s.waiting_on]}</dd>
        <dt>Thickness</dt><dd>{s.line_width} px · opacity {Math.round((s.opacity ?? 1) * 100)}%</dd>
        {#if s.text}<dt>Line text</dt><dd>“{s.text}” <span class="muted">· {s.text_align} · {s.text_position}</span></dd>{/if}
        <dt>Colour</dt><dd>{@render swatch(s.color, s.color ?? '#ffffff')}</dd>
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
        <dt>Colour</dt><dd>{@render swatch(t.color, t.color ?? '#ffffff')}</dd>
      {/if}
    </dl>

    <div class="description">
      {#if e.description}<Markdown source={e.description} />{:else}<p class="muted">No description.</p>{/if}
    </div>

    {#if type === 'states' && via}
      <p class="kicker all-lines">The “{entityName(ws, 'states', id)}” state: affects every line in it</p>
    {/if}
    <div class="actions wrap">
      <button onclick={edit}>{type === 'states' && via ? 'Edit state (all lines)' : 'Edit'}</button>
      <button onclick={editDescription}>Edit description</button>
      {#if type === 'milestones'}
        {@const m = e as Milestone}
        <button onclick={() => openForm('projects', { preset: { from: m.id, group: ws.projects.find((p) => p.id === m.project)?.group, date: m.date }, title: 'Fork from here' })}>Fork from here</button>
        <button onclick={() => openForm('milestones', { preset: { merges: [m.id], date: m.date }, title: 'Merge into…' })}>Merge into…</button>
        <button onclick={() => openForm('references', { preset: { from: m.id } })}>Add reference</button>
      {:else if type === 'projects'}
        <button onclick={() => openForm('milestones', { preset: { project: id } })}>Add milestone</button>
      {/if}
      <button class="danger" onclick={del}>{type === 'states' && via ? 'Delete state' : 'Delete'}</button>
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
  .all-lines {
    margin-top: 0.4rem;
  }
  .via {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    margin: -0.3rem 0 1rem;
    padding: 0.6rem 0.7rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--panel);
  }
  .line-text-form {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
    padding: 0.5rem 0 0.6rem;
    border-bottom: 1px solid var(--line);
  }
  .line-text-form :global(label) {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    font-size: 12.5px;
    color: var(--muted);
  }
  .via label {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    font-size: 12.5px;
    color: var(--muted);
  }
  .danger-text {
    color: var(--danger);
  }
</style>
