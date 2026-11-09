<script lang="ts">
  // Download a .tar.gz backup of a workspace, or restore one (after confirmation).
  // Without `user`: the logged-in user's own workspace. With `user` (admins only): that user's.
  import { admin, messagesOf, restoreBackup, type Schemas } from '../api/client';
  import { app, closePanel, load, showToast } from '../state.svelte';

  let { user }: { user?: string } = $props();
  const backupUrl = $derived(user ? admin.backupUrl(user) : '/api/backup');
  const restoreUrl = $derived(user ? admin.restoreUrl(user) : '/api/restore');
  const whose = $derived(user ? `${user}'s workspace` : 'the current database');

  let input: HTMLInputElement | undefined = $state();
  let file = $state<File | null>(null);
  let mismatch = $state<Schemas['VersionMismatchOut'] | null>(null);
  let errors = $state<string[]>([]);
  let busy = $state(false);

  function chosen(e: Event) {
    const f = (e.currentTarget as HTMLInputElement).files?.[0] ?? null;
    errors = [];
    mismatch = null;
    file = f;
    if (input) input.value = ''; // allow choosing the same file again later
  }

  function cancel() {
    file = null;
    mismatch = null;
    errors = [];
  }

  async function restore(force: boolean) {
    if (!file) return;
    busy = true;
    errors = [];
    try {
      const r = await restoreBackup(file, force, restoreUrl);
      if (!r.ok) {
        mismatch = r.mismatch;
        return;
      }
      const when = r.result.created ? new Date(r.result.created).toLocaleString() : 'an unknown date';
      file = null;
      mismatch = null;
      if (user) {
        showToast(`Restored ${user}'s workspace from the backup of ${when} (lineage ${r.result.restored_version}).`, false);
      } else {
        closePanel();
        await load();
        showToast(`Restored the backup from ${when} (lineage ${r.result.restored_version}).`);
      }
    } catch (e) {
      errors = messagesOf(e);
    } finally {
      busy = false;
    }
  }

  const size = (n: number) => (n < 1024 * 1024 ? `${Math.max(1, Math.round(n / 1024))} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`);
</script>

<div class="backup">
  <p class="muted small">
    A backup is one <code>.tar.gz</code> file with everything in the workspace (all entities and descriptions) and the
    lineage version that made it{app.version ? ` (this is v${app.version})` : ''}.
  </p>
  <div class="actions">
    <!-- a plain download: the browser saves it like any other file -->
    <a class="button" href={backupUrl} download>Download a backup</a>
    <button onclick={() => input?.click()} disabled={busy}>Restore from a backup…</button>
    <input bind:this={input} type="file" accept=".gz,.tgz,application/gzip" hidden onchange={chosen} />
  </div>

  {#if file && !mismatch}
    <div class="confirm" role="alertdialog" aria-label="Confirm restore">
      <strong>Restoring this file overwrites {whose}.</strong>
      <p>
        Everything now in {user ? `${user}'s workspace` : 'lineage'} (domains, groups, projects, milestones, references,
        vocabulary and descriptions) is replaced by the contents of <code>{file.name}</code> ({size(file.size)}).
        {user ? `${user} can undo it with Undo, before making other changes.` : 'You can undo it right after with Undo.'}
      </p>
      <div class="actions">
        <button class="danger" onclick={() => restore(false)} disabled={busy}>Overwrite and restore</button>
        <button onclick={cancel} disabled={busy}>Cancel</button>
      </div>
    </div>
  {/if}

  {#if file && mismatch}
    <div class="confirm" role="alertdialog" aria-label="Different version">
      <strong>This backup is from another lineage version.</strong>
      <p>
        It was made by lineage <b>{mismatch.backup_version}</b>; this is lineage <b>{mismatch.current_version}</b>. The
        data format may differ. Restoring still overwrites {whose} (it can be undone right after).
      </p>
      <div class="actions">
        <button class="danger" onclick={() => restore(true)} disabled={busy}>Restore anyway</button>
        <button onclick={cancel} disabled={busy}>Cancel</button>
      </div>
    </div>
  {/if}

  {#if errors.length}
    <ul class="errors" role="alert">{#each errors as err}<li>{err}</li>{/each}</ul>
  {/if}
</div>

<style>
  .backup {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
  }
  .actions > a,
  .actions > button {
    white-space: nowrap;
  }
  .actions {
    flex-wrap: wrap;
  }
  a.button {
    display: inline-block;
    padding: 0.25rem 0.7rem;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--bg);
    color: var(--fg);
    text-decoration: none;
  }
  a.button:hover {
    border-color: var(--muted);
  }
  .backup p {
    margin: 0;
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
  .errors {
    margin: 0;
  }
</style>
