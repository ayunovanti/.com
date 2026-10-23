#!/usr/bin/env python3
"""
Import a WordPress post into src/content/blog/ as markdown, images downloaded locally.

Usage:
  python3 scripts/import_wp_post.py --rank 2
  python3 scripts/import_wp_post.py --slug some-post-slug
  python3 scripts/import_wp_post.py --rank 3 --site https://otherblog.com

--rank N picks the Nth most recent post (1 = latest, already imported once; default 2).
"""
import argparse
import html
import json
import os
import re
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse

SITE_DEFAULT = "https://ayunovanti.com"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOG_DIR = os.path.join(PROJECT_ROOT, "src", "content", "blog")
IMAGES_ROOT = os.path.join(PROJECT_ROOT, "public", "images", "blog")

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def fetch_json(url: str):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def clean_text(s: str) -> str:
    # this site's content has a known artifact: literal backslashes before quotes/entities
    s = s.replace('\\"', '"').replace("\\'", "'")
    s = s.replace('&#8217;', "'").replace('&nbsp;', ' ')
    s = html.unescape(s)
    s = s.replace('\\', '').replace('"', '')
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def real_image_url(src: str) -> str:
    src = src.replace('\\', '').replace('"', '').strip()
    m = re.match(r'https?://i[0-2]\.wp\.com/(.+)', src)  # strip jetpack photon proxy
    if m:
        src = 'https://' + m.group(1)
    return src.split('?')[0]


class Converter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out = []
        self.buf = ''
        self.in_blockquote = False
        self.images = []
        self.pending_img = None

    def flush_para(self, prefix=''):
        text = clean_text(self.buf)
        if text:
            self.out.append(f'{prefix}{text}')
        self.buf = ''

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('em', 'i'):
            self.buf += '*'
        elif tag in ('strong', 'b'):
            self.buf += '**'
        elif tag == 'br':
            self.buf += '\n'
        elif tag == 'img':
            src = real_image_url(attrs.get('src', ''))
            alt = clean_text(attrs.get('alt', ''))
            self.pending_img = {'src': src, 'alt': alt, 'caption': ''}
        elif tag == 'blockquote':
            self.in_blockquote = True

    def handle_endtag(self, tag):
        if tag in ('em', 'i'):
            self.buf += '*'
        elif tag in ('strong', 'b'):
            self.buf += '**'
        elif tag == 'p':
            self.flush_para('> ' if self.in_blockquote else '')
        elif tag in ('h2', 'h3'):
            text = clean_text(self.buf)
            self.buf = ''
            if text:
                self.out.append(f"{'##' if tag == 'h2' else '###'} {text}")
        elif tag == 'figcaption':
            if self.pending_img is not None:
                self.pending_img['caption'] = clean_text(self.buf)
            self.buf = ''
        elif tag == 'figure':
            if self.pending_img is not None:
                img = self.pending_img
                self.images.append(img)
                alt = img['alt'] or img['caption'] or 'post image'
                self.out.append(f"![{alt}]({img['src']})")
                if img['caption']:
                    self.out.append(f"*{img['caption']}*")
                self.pending_img = None
        elif tag == 'blockquote':
            self.in_blockquote = False
        elif tag == 'cite':
            text = clean_text(self.buf).lstrip('–—- ').strip()
            self.buf = ''
            if text:
                self.out.append(f'*— {text}*')

    def handle_data(self, data):
        self.buf += data


def slugify(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')


def fetch_comments(site: str, post_id: int) -> list[dict]:
    comments = fetch_json(f"{site}/wp-json/wp/v2/comments?post={post_id}&per_page=100&order=asc")
    result = []
    for c in comments:
        content = re.sub(r'<[^>]+>', ' ', c.get('content', {}).get('rendered', ''))
        result.append({
            'author': clean_text(c.get('author_name', 'Anonymous')),
            'date': c.get('date', ''),
            'content': clean_text(content),
        })
    return result


def fetch_post(site: str, rank: int | None, slug: str | None) -> dict:
    if slug:
        url = f"{site}/wp-json/wp/v2/posts?slug={slug}&_embed"
    else:
        url = f"{site}/wp-json/wp/v2/posts?per_page=1&page={rank}&orderby=date&order=desc&_embed"
    posts = fetch_json(url)
    if not posts:
        raise SystemExit(f"No post found for {slug or f'rank {rank}'}")
    return posts[0]


def convert_post(post: dict):
    conv = Converter()
    conv.feed(post['content']['rendered'])
    conv.flush_para()
    body_md = '\n\n'.join(line for line in conv.out if line.strip())

    embedded = post.get('_embedded', {})
    meta = {
        'id': post['id'],
        'title': clean_text(post['title']['rendered']),
        'slug': post['slug'],
        'date': post['date'],
        'link': post['link'],
        'author': embedded.get('author', [{}])[0].get('name', 'admin'),
        'tags': [
            t['name']
            for group in embedded.get('wp:term', [])
            for t in group
            if t.get('taxonomy') == 'post_tag'
        ],
    }
    return meta, body_md, conv.images


def download_images(images: list[dict], slug: str) -> dict:
    dest_dir = os.path.join(IMAGES_ROOT, slug)
    os.makedirs(dest_dir, exist_ok=True)
    mapping = {}
    for img in images:
        url = img['src']
        filename = os.path.basename(urlparse(url).path)
        dest_path = os.path.join(dest_dir, filename)
        if not os.path.exists(dest_path):
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp, open(dest_path, 'wb') as out:
                out.write(resp.read())
        mapping[url] = f"/images/blog/{slug}/{filename}"
        print(f"  downloaded {filename} ({os.path.getsize(dest_path)} bytes)")
    return mapping


def yaml_escape(s: str) -> str:
    return s.replace('\\', '\\\\').replace('"', '\\"')


def write_markdown(meta: dict, body_md: str, image_map: dict, comments: list[dict], featured_image: str | None):
    for remote, local in image_map.items():
        body_md = body_md.replace(remote, local)

    date_only = meta['date'].split('T')[0]
    tags_yaml = ', '.join(f'"{yaml_escape(t)}"' for t in meta['tags'])
    title_escaped = yaml_escape(meta['title'])

    frontmatter_lines = [
        '---',
        f'title: "{title_escaped}"',
        f'date: {date_only}',
        f'author: {meta["author"]}',
        f'tags: [{tags_yaml}]',
        'draft: false',
    ]
    if featured_image:
        frontmatter_lines.append(f'featuredImage: "{featured_image}"')
    if comments:
        frontmatter_lines.append('comments:')
        for c in comments:
            frontmatter_lines.append(f'  - author: "{yaml_escape(c["author"])}"')
            frontmatter_lines.append(f'    date: {c["date"]}')
            frontmatter_lines.append(f'    content: "{yaml_escape(c["content"])}"')
    frontmatter_lines.append('---')

    frontmatter = '\n'.join(frontmatter_lines)
    full = f"""{frontmatter}

> Migrated from [{urlparse(meta['link']).netloc}]({meta['link']}).

{body_md}
"""
    out_path = os.path.join(BLOG_DIR, f"{meta['slug']}.md")
    with open(out_path, 'w') as f:
        f.write(full)
    return out_path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--site', default=SITE_DEFAULT)
    parser.add_argument('--rank', type=int, default=2, help='Nth most recent post, 1 = latest (default: 2)')
    parser.add_argument('--slug', help='import this exact WordPress slug instead of using --rank')
    args = parser.parse_args()

    post = fetch_post(args.site, args.rank, args.slug)
    meta, body_md, images = convert_post(post)
    comments = fetch_comments(args.site, meta['id'])

    print(f"title: {meta['title']}")
    print(f"slug:  {meta['slug']}")
    print(f"date:  {meta['date']}")
    print(f"images: {len(images)}")
    print(f"comments: {len(comments)}")
    if post.get('featured_media'):
        print(f"note: WP featured_media id {post['featured_media']} set, but this site's /wp-json/wp/v2/media "
              f"endpoint is broken (returns no data) -- using first in-article image as featuredImage instead.")

    image_map = download_images(images, meta['slug'])
    featured_image = image_map.get(images[0]['src']) if images else None
    out_path = write_markdown(meta, body_md, image_map, comments, featured_image)
    print(f"written: {out_path}")


if __name__ == '__main__':
    main()
