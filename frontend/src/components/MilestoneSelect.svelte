<script lang="ts">
  import { when } from '../layout/model';
  // A <select> of milestones grouped by project (project order).
  import { app } from '../state.svelte';

  let {
    value = $bindable(''),
    excludeProject = null,
    exclude = [],
    placeholder = 'Choose a milestone…',
    onpick,
  }: {
    value?: string | null;
    excludeProject?: string | null;
    exclude?: string[];
    placeholder?: string;
    onpick?: (id: string) => void;
  } = $props();

  const groups = $derived.by(() => {
    const ws = app.ws!;
    const byId = new Map(ws.milestones.map((m) => [m.id, m]));
    return ws.projects
      .filter((p) => p.id !== excludeProject)
      .map((p) => ({
        project: p,
        milestones: (ws.derived.projects[p.id]?.milestones ?? [])
          .filter((id) => !exclude.includes(id))
          .map((id) => byId.get(id)!),
      }))
      .filter((g) => g.milestones.length);
  });
</script>

<select
  value={value ?? ''}
  onchange={(e) => {
    value = e.currentTarget.value || null;
    if (value) onpick?.(value);
  }}
>
  <option value="">{placeholder}</option>
  {#each groups as g}
    <optgroup label={g.project.title}>
      {#each g.milestones as m}
        <option value={m.id}>{m.title} · {when(m.at)}{m.planned ? ' (planned)' : ''}</option>
      {/each}
    </optgroup>
  {/each}
</select>
