<script lang="ts">
  // A short sample of a line style (legend, settings lists).
  import { CAP, DASH } from './lines';

  let {
    line,
    color,
    arrow = false,
    opacity = 1,
    width = 40,
    thickness = 2.2,
  }: { line: string; color: string; arrow?: boolean; opacity?: number; width?: number; thickness?: number } = $props();
</script>

<svg {width} height="12" aria-hidden="true" {opacity}>
  <line x1="2" y1="6" x2={arrow ? width - 7 : width - 2} y2="6" stroke={color} stroke-width={Math.min(thickness, 7)}
    stroke-dasharray={DASH[line]} stroke-linecap={CAP[line]} />
  {#if arrow}<path d="M{width - 8},1.5 L{width},6 L{width - 8},10.5 z" fill={color} />{/if}
</svg>
