<script lang="ts">
  import type { EntityType } from '../api/client';
  import { app, closePanel } from '../state.svelte';
  import DeleteConfirm from './DeleteConfirm.svelte';
  import EntityView from './EntityView.svelte';
  import DescriptionForm from './forms/DescriptionForm.svelte';
  import GroupForm from './forms/GroupForm.svelte';
  import KindForm from './forms/KindForm.svelte';
  import MarkerForm from './forms/MarkerForm.svelte';
  import MilestoneForm from './forms/MilestoneForm.svelte';
  import ProjectForm from './forms/ProjectForm.svelte';
  import ReferenceForm from './forms/ReferenceForm.svelte';
  import ReftypeForm from './forms/ReftypeForm.svelte';
  import StateForm from './forms/StateForm.svelte';

  const FORMS = {
    groups: GroupForm,
    projects: ProjectForm,
    milestones: MilestoneForm,
    references: ReferenceForm,
    kinds: KindForm,
    states: StateForm,
    reftypes: ReftypeForm,
    markers: MarkerForm,
  } satisfies Record<EntityType, unknown>;

  // Remount forms whenever the panel switches to something else.
  const key = $derived(JSON.stringify(app.panel));
</script>

{#if app.panel && app.ws}
  {@const p = app.panel}
  <aside class="panel" aria-label="Details">
    <button class="close" aria-label="Close panel" onclick={closePanel}>×</button>
    {#key key}
      {#if p.kind === 'view'}
        <EntityView type={p.type} id={p.id} via={p.via} />
      {:else if p.kind === 'form'}
        {@const Form = FORMS[p.type]}
        <Form id={p.id} preset={p.preset} title={p.title} />
      {:else if p.kind === 'description'}
        <DescriptionForm type={p.type} id={p.id} />
      {:else if p.kind === 'delete'}
        <DeleteConfirm type={p.type} id={p.id} />
      {/if}
    {/key}
  </aside>
{/if}

<style>
  .panel {
    position: relative;
    width: 400px;
    flex: none;
    padding: 1rem 1.1rem 2rem;
    border-left: 1px solid var(--line);
    background: var(--bg);
    overflow-y: auto;
  }
  .close {
    position: absolute;
    top: 0.6rem;
    right: 0.6rem;
    border: none;
    font-size: 1.3rem;
    line-height: 1;
    padding: 0.1rem 0.4rem;
  }
</style>
