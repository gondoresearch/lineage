<script lang="ts">
  import { onMount } from 'svelte';
  import Filters from './components/Filters.svelte';
  import SidePanel from './components/SidePanel.svelte';
  import Toast from './components/Toast.svelte';
  import { app, applyTheme, load, openForm, routeFromHash, savedTheme, startPolling, undoLast, type Theme } from './state.svelte';
  import Dependencies from './views/Dependencies.svelte';
  import Settings from './views/Settings.svelte';
  import StatusBoard from './views/StatusBoard.svelte';
  import Timeline from './views/Timeline.svelte';

  const LABELS = { timeline: 'Timeline', status: 'Status', deps: 'Dependencies', settings: 'Settings' } as const;
  const THEMES: Theme[] = ['auto', 'light', 'dark'];
  const THEME_LABEL = { auto: 'Theme: auto', light: 'Theme: light', dark: 'Theme: dark' } as const;
  const initialTheme = savedTheme();
  let theme = $state<Theme>(initialTheme);
  applyTheme(initialTheme);
  function cycleTheme() {
    theme = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
    applyTheme(theme);
  }

  onMount(() => {
    routeFromHash();
    window.addEventListener('hashchange', routeFromHash);
    load();
    const stop = startPolling();
    return () => {
      stop();
      window.removeEventListener('hashchange', routeFromHash);
    };
  });
</script>

<div class="shell">
  <header class="toolbar">
    <span class="brand"><img src="/logo.svg" alt="" width="22" height="22" />lineage</span>
    <nav>
      {#each Object.entries(LABELS) as [id, label]}
        <a href="#/{id}" class:active={app.view === id}>{label}</a>
      {/each}
    </nav>
    <div class="tools">
      <button onclick={() => openForm('projects')} disabled={!app.ws}>Add project</button>
      <button onclick={() => openForm('groups')} disabled={!app.ws}>Add group</button>
      <button onclick={undoLast} title="Undo the last change">Undo</button>
      <button onclick={cycleTheme} title="Switch between following the system, light and dark">{THEME_LABEL[theme]}</button>
    </div>
  </header>

  {#if app.error}
    <div class="banner" role="alert">
      {#each app.error.split('\n') as line}<div>{line}</div>{/each}
    </div>
  {/if}

  {#if app.ws && app.view !== 'settings'}
    <Filters />
  {/if}

  <div class="body">
    <main>
      {#if !app.ws}
        {#if !app.error}<p class="muted">Loading…</p>{/if}
      {:else if app.view === 'timeline'}
        <Timeline ws={app.ws} />
      {:else if app.view === 'status'}
        <StatusBoard ws={app.ws} />
      {:else if app.view === 'deps'}
        <Dependencies ws={app.ws} />
      {:else}
        <Settings ws={app.ws} />
      {/if}
    </main>
    <SidePanel />
  </div>
</div>

<Toast />
