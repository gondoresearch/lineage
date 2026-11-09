// Markdown with LaTeX math ($…$ inline, $$…$$ display), sanitised for {@html}.
import { katex } from '@mdit/plugin-katex';
import DOMPurify from 'dompurify';
import MarkdownIt from 'markdown-it';
// Loaded with this module (on demand), not with the main bundle.
import 'katex/dist/katex.min.css';

const md = new MarkdownIt({ html: false, linkify: true });
md.use(katex, { throwOnError: false });

// Links in descriptions open in a new tab instead of leaving the app.
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A' && node.getAttribute('href')) {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer');
  }
});

export function renderMarkdown(source: string): string {
  // KaTeX emits HTML (with inline styles), MathML and, for some constructs, SVG.
  return DOMPurify.sanitize(md.render(source), {
    USE_PROFILES: { html: true, mathMl: true, svg: true },
    ADD_ATTR: ['target'],
  });
}
