// Derive a heading outline (table of contents) + reading stats from a note's
// Markdown body. Pure functions — no DOM, no editor coupling.
import type { OutlineItem } from './types';

function slug(text: string, i: number): string {
  const base = text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return `${base || 'h'}-${i}`;
}

/** Extract H1–H3 headings, skipping fenced code blocks. */
export function parseOutline(body: string): OutlineItem[] {
  const items: OutlineItem[] = [];
  let inFence = false;
  let i = 0;
  for (const line of body.split('\n')) {
    if (/^\s*(```|~~~)/.test(line)) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;
    const m = /^(#{1,3})\s+(.+?)\s*#*$/.exec(line);
    if (m) {
      const text = m[2].replace(/[*_`~]/g, '').trim();
      items.push({ level: m[1].length, text, id: slug(text, i++) });
    }
  }
  return items;
}

/** Word count over body text with Markdown punctuation/code stripped. */
export function wordCount(body: string): number {
  const text = body
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`[^`]*`/g, ' ')
    .replace(/[#>*_~[\]()!|-]/g, ' ');
  const words = text.trim().split(/\s+/).filter(Boolean);
  return words.length;
}

/** Reading time in minutes at ~200 wpm (min 1 once there is any text). */
export function readingMinutes(words: number): number {
  return words === 0 ? 0 : Math.max(1, Math.round(words / 200));
}
