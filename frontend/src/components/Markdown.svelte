<script lang="ts" module>
  // The renderer (markdown-it, KaTeX, DOMPurify) is loaded on first use, so it is not
  // part of the main bundle. One shared load for every instance.
  type Render = (source: string) => string;
  let loading: Promise<Render> | null = null;
  const loadRenderer = () => (loading ??= import('../lib/markdown').then((m) => m.renderMarkdown));
</script>

<script lang="ts">
  let { source }: { source: string } = $props();
  let render = $state<Render | null>(null);
  loadRenderer().then((r) => (render = r));
  const html = $derived(render ? render(source) : '');
</script>

<div class="md">{@html html}</div>
