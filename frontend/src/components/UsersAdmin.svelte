<script lang="ts">
  // Admins only: the accounts of this lineage. Admin accounts are listed but managed
  // with the command line; for the others: set password, back up / restore, delete.
  import { onMount } from 'svelte';
  import { admin, messagesOf, type User } from '../api/client';
  import { app, showToast } from '../state.svelte';
  import BackupRestore from './BackupRestore.svelte';

  const MIN = 8;
  let users = $state<User[]>([]);
  let errors = $state<string[]>([]);
  /** the row whose action panel is open */
  let open = $state<{ name: string; action: 'password' | 'backup' | 'delete' } | null>(null);
  let busy = $state(false);

  let newName = $state('');
  let newPassword = $state('');
  let password = $state('');
  let purge = $state(false);

  async function refresh() {
    try {
      users = await admin.users();
      errors = [];
    } catch (e) {
      errors = messagesOf(e);
    }
  }
  onMount(refresh);

  function toggle(name: string, action: 'password' | 'backup' | 'delete') {
    open = open?.name === name && open.action === action ? null : { name, action };
    password = '';
    purge = false;
    errors = [];
  }

  async function run(fn: () => Promise<unknown>, done: string) {
    busy = true;
    errors = [];
    try {
      await fn();
      showToast(done, false);
      open = null;
      await refresh();
    } catch (e) {
      errors = messagesOf(e);
    } finally {
      busy = false;
    }
  }

  function create(e: SubmitEvent) {
    e.preventDefault();
    const name = newName.trim();
    run(async () => {
      await admin.create(name, newPassword);
      newName = newPassword = '';
    }, `Created ${name}.`);
  }

  function setPassword(e: SubmitEvent, name: string) {
    e.preventDefault();
    run(() => admin.setPassword(name, password), `Password of ${name} changed; their sessions have ended.`);
  }

  function remove(name: string) {
    run(() => admin.remove(name, purge), purge ? `Deleted ${name} and their workspace.` : `Deleted ${name}; their workspace folder is kept.`);
  }

  const date = (iso: string | null | undefined) => (iso ? new Date(iso).toLocaleDateString() : '');
</script>

<div class="users">
  <p class="muted small">
    Every account has its own private workspace. Admins can add and delete accounts, set their passwords and back up or
    restore their workspaces, but cannot open them. Admin accounts are managed with the command line
    (<code>python -m backend.manage admin NAME on|off</code>).
  </p>

  <table>
    <thead><tr><th>User</th><th>Created</th><th></th></tr></thead>
    <tbody>
      {#each users as u (u.username)}
        <tr>
          <td>
            <span class="who"><b>{u.username}</b>
              {#if u.admin}<span class="badge">admin</span>{/if}
              {#if u.username === app.user}<span class="muted small">(you)</span>{/if}</span>
          </td>
          <td class="muted small">{date(u.created)}</td>
          <td><div class="row-actions">
            {#if !u.admin}
              <button class:on={open?.name === u.username && open.action === 'password'} onclick={() => toggle(u.username, 'password')}>Set password</button>
              <button class:on={open?.name === u.username && open.action === 'backup'} onclick={() => toggle(u.username, 'backup')}>Backup…</button>
              <button class="danger" class:on={open?.name === u.username && open.action === 'delete'} onclick={() => toggle(u.username, 'delete')}>Delete</button>
            {/if}
          </div></td>
        </tr>
        {#if open?.name === u.username}
          <tr class="panel">
            <td colspan="3">
              {#if open.action === 'password'}
                <form class="form inline" onsubmit={(e) => setPassword(e, u.username)}>
                  <label>
                    <span>New password for {u.username} (at least {MIN} characters)</span>
                    <input type="password" bind:value={password} autocomplete="new-password" />
                  </label>
                  <div class="actions">
                    <button type="submit" disabled={busy || password.length < MIN}>Set password</button>
                    <button type="button" onclick={() => (open = null)}>Cancel</button>
                  </div>
                  <p class="muted small">{u.username} is logged out everywhere.</p>
                </form>
              {:else if open.action === 'backup'}
                <BackupRestore user={u.username} />
              {:else}
                <div class="confirm" role="alertdialog" aria-label="Confirm delete">
                  <strong>Delete the account {u.username}?</strong>
                  <label class="check"><input type="checkbox" bind:checked={purge} /> Also delete their workspace (cannot be undone)</label>
                  <p class="muted small">
                    {purge
                      ? 'Their projects and history are deleted from the server.'
                      : 'Their workspace folder stays on the server; an account created later with the same name gets it back.'}
                  </p>
                  <div class="actions">
                    <button class="danger" onclick={() => remove(u.username)} disabled={busy}>Delete {u.username}</button>
                    <button onclick={() => (open = null)} disabled={busy}>Cancel</button>
                  </div>
                </div>
              {/if}
            </td>
          </tr>
        {/if}
      {/each}
    </tbody>
  </table>

  {#if errors.length}
    <ul class="errors" role="alert">{#each errors as err}<li>{err}</li>{/each}</ul>
  {/if}

  <form class="form add" onsubmit={create}>
    <h3>Add a user</h3>
    <div class="fields">
      <label>
        <span>User name</span>
        <input bind:value={newName} autocomplete="off" autocapitalize="none" spellcheck="false" placeholder="lowercase, digits, - or _" />
      </label>
      <label>
        <span>Password (at least {MIN} characters)</span>
        <input type="password" bind:value={newPassword} autocomplete="new-password" />
      </label>
    </div>
    <div class="actions">
      <button type="submit" disabled={busy || !newName.trim() || newPassword.length < MIN}>Add user</button>
    </div>
  </form>
</div>

<style>
  .users {
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
    max-width: 720px;
  }
  .users p {
    margin: 0;
  }
  table {
    border-collapse: collapse;
    width: 100%;
  }
  th {
    text-align: left;
    font-weight: 500;
    font-size: 12.5px;
    color: var(--muted);
    padding: 0.3rem 0.4rem;
    border-bottom: 1px solid var(--line);
  }
  td {
    padding: 0.4rem;
    border-bottom: 1px solid var(--line);
    vertical-align: middle;
  }
  .row-actions {
    display: flex;
    gap: 0.35rem;
    justify-content: flex-end;
    flex-wrap: wrap;
  }
  .who {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.35rem;
  }
  .badge {
    padding: 0 0.4rem;
    border-radius: 999px;
    font-size: 11px;
    background: var(--accent-bg);
    color: var(--accent);
  }
  tr.panel td {
    background: var(--panel);
    padding: 0.7rem 0.8rem;
  }
  .inline {
    max-width: 360px;
  }
  .confirm {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.7rem 0.8rem;
    border: 1.5px solid var(--danger);
    border-radius: 8px;
    background: var(--danger-bg);
  }
  .confirm strong {
    color: var(--danger);
  }
  .check {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }
  .add h3 {
    margin: 0;
    font-size: 14px;
  }
  .add .fields {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
  }
  .add .fields label {
    flex: 1 1 200px;
  }
  @media (max-width: 560px) {
    .row-actions {
      justify-content: flex-start;
    }
  }
</style>
