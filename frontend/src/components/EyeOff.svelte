<script lang="ts">
  // "Eye closed" icon: marks a hidden legend entry.
  let { size = 14 }: { size?: number } = $props();
</script>

<svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-label="hidden" role="img">
  <path d="M1.5 8s2.3-4 6.5-4 6.5 4 6.5 4-2.3 4-6.5 4S1.5 8 1.5 8Z" />
  <circle cx="8" cy="8" r="1.8" />
  <path d="M2.5 13.5 13.5 2.5" />
</svg>
