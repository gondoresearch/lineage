<script lang="ts">
  // Optional text drawn with a line, and where it goes.
  type Align = 'left' | 'center' | 'right';
  type Position = 'above' | 'middle' | 'below';
  type Orientation = 'horizontal' | 'along';
  let {
    text = $bindable(''),
    align = $bindable<Align>('center'),
    position = $bindable<Position>('above'),
    alongLabels = ['left', 'centre', 'right'],
    orientation = $bindable<Orientation | null>(null),
    size = $bindable(10),
    label = 'Line text',
  }: {
    text?: string;
    align?: Align;
    position?: Position;
    alongLabels?: [string, string, string];
    /** references only (lane lines are horizontal anyway); null hides the choice */
    orientation?: Orientation | null;
    /** font size in px */
    size?: number;
    label?: string;
  } = $props();
</script>

<label>{label} <span class="muted">(optional; shown on the timeline when set)</span>
  <input bind:value={text} placeholder="e.g. waiting for referees" />
</label>
{#if text}
  <div class="text-place">
    <label>Along the line
      <select bind:value={align}>
        <option value="left">{alongLabels[0]}</option>
        <option value="center">{alongLabels[1]}</option>
        <option value="right">{alongLabels[2]}</option>
      </select>
    </label>
    <label>Relative to the line
      <select bind:value={position}>
        <option value="above">above</option>
        <option value="middle">on the line</option>
        <option value="below">below</option>
      </select>
    </label>
    <label>Text size
      <span class="size">
        <input type="range" min="7" max="24" step="1" bind:value={size} />
        <span>{size} px</span>
      </span>
    </label>
    {#if orientation !== null}
      <label>Text direction
        <select bind:value={orientation}>
          <option value="horizontal">horizontal (forced)</option>
          <option value="along">along the line</option>
        </select>
      </label>
    {/if}
  </div>
{/if}

<style>
  .size {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--fg);
  }
  .size input {
    flex: 1;
  }
  .text-place {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.6rem;
  }
</style>
