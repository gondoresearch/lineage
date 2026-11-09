<script lang="ts">
  // The login screen, shown instead of the app when no one is logged in.
  import { ApiError, messagesOf } from '../api/client';
  import { app, logIn } from '../state.svelte';

  let username = $state('');
  let password = $state('');
  let error = $state<string | null>(null);
  let busy = $state(false);

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    busy = true;
    error = null;
    try {
      await logIn(username.trim(), password);
      password = '';
    } catch (err) {
      error = err instanceof ApiError || err instanceof Error ? messagesOf(err).join(' ') : String(err);
    } finally {
      busy = false;
    }
  }
</script>

<div class="login-page">
  <form class="form login" onsubmit={submit}>
    <h1 class="brand"><img src="/logo.svg" alt="" width="28" height="28" />lineage
      {#if app.version}<span class="version">v{app.version}</span>{/if}
    </h1>
    <label>
      <span>User name</span>
      <!-- svelte-ignore a11y_autofocus -->
      <input bind:value={username} autocomplete="username" autocapitalize="none" spellcheck="false" required autofocus />
    </label>
    <label>
      <span>Password</span>
      <input type="password" bind:value={password} autocomplete="current-password" required />
    </label>
    {#if error}<div class="errors" role="alert">{error}</div>{/if}
    {#if app.error}<div class="errors" role="alert">{app.error}</div>{/if}
    <button class="primary" type="submit" disabled={busy || !username.trim() || !password}>Log in</button>
  </form>
</div>

<style>
  .login-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    background: var(--panel);
  }
  .login {
    width: 100%;
    max-width: 320px;
    padding: 1.5rem;
    border: 1px solid var(--line);
    border-radius: 10px;
    background: var(--bg);
  }
  h1 {
    margin: 0 0 0.4rem;
    font-size: 20px;
  }
  .errors {
    padding: 0.5rem 0.8rem;
    font-size: 13px;
  }
  button {
    padding: 0.4rem 0.7rem;
  }
</style>
