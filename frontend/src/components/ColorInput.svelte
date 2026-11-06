<script lang="ts">
  // Native colour picker plus Clear (null = inherit along the colour chain).
  let {
    value = $bindable(null),
    allowClear = true,
    onchange,
  }: { value?: string | null; allowClear?: boolean; onchange?: (v: string | null) => void } = $props();

  function set(v: string | null) {
    value = v;
    onchange?.(v);
  }
</script>

<span class="color-input">
  <input type="color" value={value ?? '#999999'} onchange={(e) => set(e.currentTarget.value)} />
  {#if value}
    <code>{value}</code>
    {#if allowClear}<button type="button" onclick={() => set(null)}>Clear</button>{/if}
  {:else}
    <span class="muted">inherit</span>
  {/if}
</span>

<style>
  .color-input {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
  }
  input[type='color'] {
    width: 2.2rem;
    height: 1.7rem;
    padding: 0 2px;
    border: 1px solid var(--line);
    border-radius: 4px;
    background: var(--bg);
  }
  code {
    font-size: 12px;
  }
</style>
