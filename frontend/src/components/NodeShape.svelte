<script lang="ts">
  // A milestone marker. Every shape stays within radius r, where lines are cut
  // (see R in layout/timeline.ts). Open shapes have no fill, so a line is never
  // hidden behind a fill: it stops at the node edge instead.
  let { shape, x, y, r, color }: { shape: string; x: number; y: number; r: number; color: string } = $props();

  const filled = $derived(shape.startsWith('filled-'));
  const base = $derived(shape === 'open-circle' ? 'circle' : shape.replace(/^filled-/, ''));
  const fill = $derived(filled ? color : 'none');

  const pts = (offsets: [number, number][]) => offsets.map(([dx, dy]) => `${x + dx},${y + dy}`).join(' ');
  // Polygon outlines sit half a stroke inside r so their outer edge is at r.
  const p = $derived(r - 0.5);
  const square = $derived(p * 0.74);
  const star = $derived(
    Array.from({ length: 10 }, (_, i): [number, number] => {
      const rad = i % 2 === 0 ? p : p * 0.45;
      const a = -Math.PI / 2 + (i * Math.PI) / 5;
      return [rad * Math.cos(a), rad * Math.sin(a)];
    }),
  );
  const a = $derived(r * 0.72);
  // Four arrows (✥): shaft half-width sw, head half-width hw, head base at hb, tips at p.
  const arrows = $derived.by(() => {
    const sw = p * 0.16;
    const hw = p * 0.42;
    const hb = p * 0.5;
    const quarter: [number, number][] = [[0, -p], [hw, -hb], [sw, -hb], [sw, -sw]];
    const pts: [number, number][] = [];
    for (let k = 0; k < 4; k++) {
      // rotate the top quarter by k × 90° clockwise
      for (const [x0, y0] of quarter) pts.push(k === 0 ? [x0, y0] : k === 1 ? [-y0, x0] : k === 2 ? [-x0, -y0] : [y0, -x0]);
    }
    return pts;
  });
</script>

{#if base === 'circle'}
  <circle cx={x} cy={y} r={r - 1} {fill} stroke={color} stroke-width="2" />
{:else if base === 'diamond'}
  <polygon points={pts([[0, -p], [p, 0], [0, p], [-p, 0]])} {fill} stroke={color} stroke-width="2" stroke-linejoin="round" />
{:else if base === 'square'}
  <polygon points={pts([[-square, -square], [square, -square], [square, square], [-square, square]])} {fill} stroke={color} stroke-width="2" stroke-linejoin="round" />
{:else if base === 'triangle'}
  <polygon points={pts([[0, -p], [p * 0.866, p * 0.5], [-p * 0.866, p * 0.5]])} {fill} stroke={color} stroke-width="2" stroke-linejoin="round" />
{:else if base === 'star'}
  <polygon points={pts(star)} {fill} stroke={color} stroke-width="1.6" stroke-linejoin="round" />
{:else if base === 'arrows'}
  <polygon points={pts(arrows)} {fill} stroke={color} stroke-width={filled ? 1 : 1.3} stroke-linejoin="round" />
{:else if base === 'cross'}
  <path d="M{x - a},{y - a} L{x + a},{y + a} M{x + a},{y - a} L{x - a},{y + a}" stroke={color} stroke-width="2.4" stroke-linecap="round" />
{:else}
  <circle cx={x} cy={y} r={r - 1} fill="none" stroke={color} stroke-width="2" />
{/if}
