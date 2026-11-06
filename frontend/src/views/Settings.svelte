<script lang="ts">
  import { api, messagesOf, type EntityType, type Workspace } from '../api/client';
  import ColorInput from '../components/ColorInput.svelte';
  import LineSample from '../components/LineSample.svelte';
  import MarkerIcon from '../components/MarkerIcon.svelte';
  import NodeShape from '../components/NodeShape.svelte';
  import { MARKER_NEUTRAL, NEUTRAL } from '../layout/colors';
  import { app, change, isSelected, openForm, select, showToast } from '../state.svelte';

  let { ws }: { ws: Workspace } = $props();
  const WAIT = { me: 'on me', others: 'on others', nobody: 'inactive' } as const;

  async function move(id: string, position: number, type: 'groups' | 'domains' = 'groups') {
    try {
      await change(() => api.update(type, id, { position }), type === 'groups' ? 'Moved group.' : 'Moved domain.');
    } catch (e) {
      showToast(messagesOf(e).join(' '), false);
    }
  }

  async function saveWidth(field: 'fork_width' | 'merge_width', value: number) {
    try {
      await change(() => api.updateSettings({ [field]: value }), `Saved ${field === 'fork_width' ? 'fork' : 'merge'} line thickness.`);
    } catch (e) {
      showToast(messagesOf(e).join(' '), false);
    }
  }

  async function saveLineColor(field: 'fork_color' | 'merge_color', value: string | null) {
    try {
      await change(() => api.updateSettings({ [field]: value }), `Saved ${field === 'fork_color' ? 'fork' : 'merge'} line colour.`);
    } catch (e) {
      showToast(messagesOf(e).join(' '), false);
    }
  }
</script>

{#snippet header(title: string, type: EntityType, newLabel: string)}
  <div class="head">
    <h2>{title}</h2>
    <button onclick={() => openForm(type)}>{newLabel}</button>
  </div>
{/snippet}


<div class="settings">
  <section>
    {@render header('Domains', 'domains', 'New domain')}
    <ul class="rows">
      {#each ws.domains ?? [] as dm, i (dm.id)}
        <li class:selected={isSelected('domains', dm.id)}>
          <button class="row" onclick={() => select('domains', dm.id)}>
            <span class="sw" style:background={dm.color ?? 'var(--line)'}></span>{dm.name}
            <span class="muted">{ws.groups.filter((g) => g.domain === dm.id).length} groups</span>
          </button>
          <span class="order">
            <button aria-label="Move {dm.name} up" disabled={i === 0} onclick={() => move(dm.id, i - 1, 'domains')}>↑</button>
            <button aria-label="Move {dm.name} down" disabled={i === (ws.domains ?? []).length - 1} onclick={() => move(dm.id, i + 1, 'domains')}>↓</button>
          </span>
        </li>
      {:else}
        <li class="muted">No domains yet. Groups without a domain are listed first on the timeline.</li>
      {/each}
    </ul>
  </section>

  <section>
    {@render header('Groups', 'groups', 'New group')}
    <ul class="rows">
      {#each ws.groups as g, i (g.id)}
        <li class:selected={isSelected('groups', g.id)}>
          <button class="row" onclick={() => select('groups', g.id)}>
            <span class="sw" style:background={g.color}></span>{g.name}
            <span class="muted">{g.domain ? `${(ws.domains ?? []).find((d) => d.id === g.domain)?.name} · ` : ''}{ws.projects.filter((p) => p.group === g.id).length} projects</span>
          </button>
          <span class="order">
            <button aria-label="Move {g.name} up" disabled={i === 0} onclick={() => move(g.id, i - 1)}>↑</button>
            <button aria-label="Move {g.name} down" disabled={i === ws.groups.length - 1} onclick={() => move(g.id, i + 1)}>↓</button>
          </span>
        </li>
      {:else}
        <li class="muted">No groups yet.</li>
      {/each}
    </ul>
  </section>

  <section>
    {@render header('Kinds', 'kinds', 'New kind')}
    <ul class="rows">
      {#each ws.kinds as k (k.id)}
        <li class:selected={isSelected('kinds', k.id)}>
          <button class="row" onclick={() => select('kinds', k.id)}>
            <svg width="16" height="16" aria-hidden="true"><NodeShape shape={k.shape} x={8} y={8} r={6} color={k.color ?? NEUTRAL} /></svg>
            {k.name}
            <span class="muted">{k.default_state ? `→ ${ws.states.find((s) => s.id === k.default_state)?.name}` : ''}</span>
          </button>
        </li>
      {/each}
    </ul>
  </section>

  <section>
    {@render header('States', 'states', 'New state')}
    <ul class="rows">
      {#each ws.states as s (s.id)}
        <li class:selected={isSelected('states', s.id)}>
          <button class="row" onclick={() => select('states', s.id)}>
            <LineSample line={s.line} color={s.color ?? NEUTRAL} opacity={s.opacity} />{s.name} <span class="muted">{WAIT[s.waiting_on]}</span>
          </button>
        </li>
      {/each}
    </ul>
  </section>

  <section>
    {@render header('Reference types', 'reftypes', 'New reference type')}
    <ul class="rows">
      {#each ws.reftypes as t (t.id)}
        <li class:selected={isSelected('reftypes', t.id)}>
          <button class="row" onclick={() => select('reftypes', t.id)}>
            <LineSample line={t.line} color={t.color ?? NEUTRAL} arrow={t.directed} opacity={t.opacity} />{t.name} <span class="muted">{t.directed ? 'directed' : 'undirected'}</span>
          </button>
        </li>
      {/each}
    </ul>
  </section>

  <section>
    {@render header('Markers', 'markers', 'New marker')}
    <ul class="rows">
      {#each ws.markers ?? [] as mk (mk.id)}
        <li class:selected={isSelected('markers', mk.id)}>
          <button class="row" onclick={() => select('markers', mk.id)}>
            <svg width="16" height="16" aria-hidden="true"><MarkerIcon icon={mk.icon} x={8} y={8} size={13} color={mk.color ?? MARKER_NEUTRAL} /></svg>
            {mk.name}
            <span class="muted">{ws.milestones.filter((m) => m.markers?.includes(mk.id)).length} milestones</span>
          </button>
        </li>
      {:else}
        <li class="muted">No markers yet.</li>
      {/each}
    </ul>
  </section>

  <section>
    <div class="head"><h2>Fork and merge lines</h2></div>
    <div class="colors">
      <span>Fork lines</span>
      <ColorInput value={ws.settings.fork_color} onchange={(v) => saveLineColor('fork_color', v)} />
      <span>Merge lines</span>
      <ColorInput value={ws.settings.merge_color} onchange={(v) => saveLineColor('merge_color', v)} />
      <span>Fork thickness</span>
      <span class="width">
        <input type="range" min="0.5" max="8" step="0.5" value={ws.settings.fork_width}
          onchange={(e) => saveWidth('fork_width', Number(e.currentTarget.value))} />
        {ws.settings.fork_width} px
      </span>
      <span>Merge thickness</span>
      <span class="width">
        <input type="range" min="0.5" max="8" step="0.5" value={ws.settings.merge_width}
          onchange={(e) => saveWidth('merge_width', Number(e.currentTarget.value))} />
        {ws.settings.merge_width} px
      </span>
    </div>
    <p class="muted small">Without a colour, a fork line takes the forked project's colour and a merge line the source project's.</p>
  </section>
</div>

<style>
  .settings {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1.5rem 2rem;
    max-width: 1100px;
  }
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.4rem;
  }
  h2 {
    margin: 0;
    font-size: 15px;
  }
  .rows {
    list-style: none;
    margin: 0;
    padding: 0;
    border: 1px solid var(--line);
    border-radius: 8px;
  }
  .rows li {
    display: flex;
    align-items: center;
    border-top: 1px solid var(--line);
  }
  .rows li:first-child {
    border-top: none;
  }
  .rows li.muted {
    padding: 0.5rem 0.7rem;
  }
  .rows li.selected {
    background: var(--panel);
  }
  .row {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    border: none;
    border-radius: 0;
    background: transparent;
    padding: 0.45rem 0.7rem;
    text-align: left;
  }
  .row .muted {
    margin-left: auto;
    font-size: 12px;
    white-space: nowrap;
  }
  .order {
    display: flex;
    gap: 0.2rem;
    padding-right: 0.5rem;
  }
  .order button {
    padding: 0.05rem 0.45rem;
  }
  .sw {
    width: 12px;
    height: 12px;
    border-radius: 3px;
  }
  .width {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    white-space: nowrap;
  }
  .colors {
    display: grid;
    grid-template-columns: max-content auto;
    gap: 0.6rem 1rem;
    align-items: center;
  }
</style>
