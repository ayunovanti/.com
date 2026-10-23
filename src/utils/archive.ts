import type { CollectionEntry } from 'astro:content';

export interface ArchiveGroup {
  key: string;
  label: string;
  posts: CollectionEntry<'blog'>[];
}

export function groupByMonth(posts: CollectionEntry<'blog'>[]): ArchiveGroup[] {
  const groups = new Map<string, ArchiveGroup>();

  for (const post of posts) {
    const d = post.data.date;
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    const label = d.toLocaleString('en-US', { month: 'long', year: 'numeric' });

    if (!groups.has(key)) groups.set(key, { key, label, posts: [] });
    groups.get(key)!.posts.push(post);
  }

  return [...groups.values()].sort((a, b) => (a.key < b.key ? 1 : -1));
}
