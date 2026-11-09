<script lang="ts">
  // Change the logged-in user's password. Other sessions of the user end; this one stays.
  import { auth, messagesOf } from '../api/client';
  import { showToast } from '../state.svelte';

  const MIN = 8;
  let current = $state('');
  let next = $state('');
  let repeat = $state('');
  let errors = $state<string[]>([]);
  let busy = $state(false);

  const mismatch = $derived(repeat !== '' && next !== repeat);
  const ready = $derived(current !== '' && next.length >= MIN && next === repeat);

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    busy = true;
    errors = [];
    try {
      await auth.changePassword(current, next);
      current = next = repeat = '';
      showToast('Password changed. Other sessions have been logged out.', false);
    } catch (err) {
      errors = messagesOf(err);
    } finally {
      busy = false;
    }
  }
</script>

<form class="form password" onsubmit={submit}>
  <label>
    <span>Current password</span>
    <input type="password" bind:value={current} autocomplete="current-password" />
  </label>
  <label>
    <span>New password (at least {MIN} characters)</span>
    <input type="password" bind:value={next} autocomplete="new-password" />
  </label>
  <label>
    <span>Repeat the new password</span>
    <input type="password" bind:value={repeat} autocomplete="new-password" />
  </label>
  {#if mismatch}<p class="muted small">The new passwords do not match.</p>{/if}
  {#if errors.length}
    <ul class="errors" role="alert">{#each errors as err}<li>{err}</li>{/each}</ul>
  {/if}
  <div class="actions">
    <button type="submit" disabled={busy || !ready}>Change password</button>
  </div>
</form>

<style>
  .password {
    max-width: 360px;
  }
  .password p {
    margin: 0;
  }
</style>
