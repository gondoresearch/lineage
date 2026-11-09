<script lang="ts">
  // Shown instead of the app while the account must choose a new password (the default admin).
  import { app, load, logOut } from '../state.svelte';
  import ChangePassword from './ChangePassword.svelte';

  async function changed() {
    app.mustChange = false;
    await load();
  }
</script>

<div class="page">
  <div class="card">
    <h1 class="brand"><img src="/logo.svg" alt="" width="28" height="28" />lineage</h1>
    <h2>Choose a new password</h2>
    <p class="muted">
      <b>{app.user}</b> still has its first password. Choose your own before using lineage: anyone who knows
      the default could otherwise log in as {app.user}.
    </p>
    <ChangePassword onchanged={changed} />
    <button class="link" onclick={logOut}>Log out</button>
  </div>
</div>

<style>
  .page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    background: var(--panel);
  }
  .card {
    width: 100%;
    max-width: 380px;
    padding: 1.5rem;
    border: 1px solid var(--line);
    border-radius: 10px;
    background: var(--bg);
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
  }
  h1 {
    margin: 0;
    font-size: 20px;
  }
  h2 {
    margin: 0.4rem 0 0;
    font-size: 16px;
  }
  p {
    margin: 0;
  }
  .link {
    align-self: flex-start;
  }
</style>
