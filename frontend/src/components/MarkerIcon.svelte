<script lang="ts">
  // A marker badge icon, drawn in a 12×12 box centred on (x, y) and scaled to `size`.
  let { icon, x, y, size = 11, color }: { icon: string; x: number; y: number; size?: number; color: string } = $props();
  const k = $derived(size / 12);
</script>

<g transform="translate({x - size / 2},{y - size / 2}) scale({k})" class="marker-icon">
  {#if icon === 'warning'}
    <path d="M6,0.6 L11.6,11 L0.4,11 Z" fill={color} stroke={color} stroke-width="0.8" stroke-linejoin="round" />
    <path d="M6,4 L6,7.4" stroke="#fff" stroke-width="1.5" stroke-linecap="round" />
    <circle cx="6" cy="9.2" r="0.85" fill="#fff" />
  {:else if icon === 'question'}
    <circle cx="6" cy="6" r="5.6" fill={color} />
    <path d="M4.1,4.6 C4.1,2.2 7.9,2.2 7.9,4.4 C7.9,5.9 6,5.9 6,7.3" fill="none" stroke="#fff" stroke-width="1.4" stroke-linecap="round" />
    <circle cx="6" cy="9.2" r="0.85" fill="#fff" />
  {:else if icon === 'info'}
    <circle cx="6" cy="6" r="5.6" fill={color} />
    <circle cx="6" cy="3.4" r="0.9" fill="#fff" />
    <path d="M6,5.4 L6,9.2" stroke="#fff" stroke-width="1.5" stroke-linecap="round" />
  {:else if icon === 'check'}
    <circle cx="6" cy="6" r="5.6" fill={color} />
    <path d="M3.4,6.2 L5.3,8.1 L8.8,4.2" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
  {:else if icon === 'chain'}
    <g fill="none" stroke={color} stroke-width="1.6" transform="rotate(-45 6 6)">
      <rect x="0.6" y="3.9" width="6" height="4.2" rx="2.1" />
      <rect x="5.4" y="3.9" width="6" height="4.2" rx="2.1" />
    </g>
  {:else if icon === 'flag'}
    <path d="M2.2,11.4 L2.2,0.8" stroke={color} stroke-width="1.4" stroke-linecap="round" />
    <path d="M2.8,1 L10.8,3.6 L2.8,6.4 Z" fill={color} stroke={color} stroke-width="0.6" stroke-linejoin="round" />
  {:else if icon === 'pin'}
    <path d="M6,11.6 C6,11.6 1.6,6.9 1.6,4.5 A4.4,4.4 0 0 1 10.4,4.5 C10.4,6.9 6,11.6 6,11.6 Z" fill={color} />
    <circle cx="6" cy="4.5" r="1.6" fill="#fff" />
  {:else if icon === 'clock'}
    <circle cx="6" cy="6" r="5" fill="var(--bg)" stroke={color} stroke-width="1.5" />
    <path d="M6,3 L6,6.2 L8.2,7.5" fill="none" stroke={color} stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" />
  {:else if icon === 'lock'}
    <path d="M3.4,5.4 L3.4,3.8 A2.6,2.6 0 0 1 8.6,3.8 L8.6,5.4" fill="none" stroke={color} stroke-width="1.4" />
    <rect x="1.8" y="5.2" width="8.4" height="6.2" rx="1.2" fill={color} />
    <circle cx="6" cy="8.1" r="0.95" fill="#fff" />
  {/if}
</g>
