export function makeExcerpt(markdown: string, length = 160): string {
  const text = markdown
    .split('\n')
    .filter((line) => !line.trim().startsWith('>')) // drop blockquotes (e.g. migration notices)
    .join('\n')
    .replace(/!\[.*?\]\(.*?\)/g, '') // images
    .replace(/\[(.*?)\]\(.*?\)/g, '$1') // links -> text
    .replace(/^#+\s*/gm, '') // headings
    .replace(/[*_`]/g, '') // emphasis/code markers
    .replace(/\s+/g, ' ')
    .trim();

  if (text.length <= length) return text;

  const cut = text.slice(0, length);
  return `${cut.slice(0, cut.lastIndexOf(' '))}…`;
}
