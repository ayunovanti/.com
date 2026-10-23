# Blog — Astro + Cloudflare Pages + Sveltia CMS (free tier)

Static site on Cloudflare Pages (free), content as markdown in this repo, admin UI at `/admin` editable from any browser via GitHub login. No server, no DB to secure.

Requires Node 22+ (pinned via Volta in `package.json`, Cloudflare Pages build image supports it via `NODE_VERSION` env var).

## Local dev

```
npm install
npm run dev
```

Posts live in `src/content/blog/*.md`.

## Deploy — Cloudflare Pages

1. Push this repo to GitHub.
2. Cloudflare dashboard → Workers & Pages → Create → Pages → connect the GitHub repo.
3. Build command: `npm run build`, output directory: `dist`.
4. Environment variable: `NODE_VERSION = 22`.
5. Deploy. Free tier covers this (static site, generous bandwidth/build minutes).

## Admin UI (Sveltia CMS) — GitHub OAuth via Cloudflare Worker

Sveltia needs a tiny OAuth proxy so the admin can log in with GitHub. `oauth-worker/` is that proxy, deployed as a free Cloudflare Worker.

Worker is already deployed: `https://blog-cms-auth.madewith.workers.dev` (repo `ayunovanti/.com` is set in `public/admin/config.yml`). Remaining step is yours — GitHub doesn't let this be automated:

1. GitHub → Settings → Developer settings → OAuth Apps → New OAuth App.
   - Homepage URL: your Pages URL (once deployed).
   - Authorization callback URL: `https://blog-cms-auth.madewith.workers.dev/callback`
2. Set the secrets on the worker (run these yourself so the values never leave your terminal):
   ```
   cd oauth-worker
   npx wrangler secret put GITHUB_CLIENT_ID
   npx wrangler secret put GITHUB_CLIENT_SECRET
   ```
3. Once the Pages site is deployed, visit `https://your-site.pages.dev/admin` to log in with GitHub and write posts.

Every save commits a markdown file to the repo → Cloudflare Pages auto-rebuilds and deploys.

## Security

- No database, no server process, no login system of your own to patch — smallest attack surface of all three options discussed.
- Auth is GitHub's OAuth (2FA on your GitHub account = 2FA on the CMS).
- Keep `GITHUB_CLIENT_SECRET` only in the Worker's secret store (`wrangler secret put`), never in a file.
- Cloudflare Pages serves over HTTPS by default.
- `npm audit` currently clean (0 vulnerabilities) — re-run after dependency bumps.

## Migrate from WordPress

1. WordPress admin → Tools → Export → All content (downloads `.xml`).
2. Convert to markdown:
   ```
   npx wordpress-export-to-markdown
   ```
   Point it at the exported XML; it writes one `.md` file per post with frontmatter (title, date, author) plus downloads images locally.
3. Copy the generated `.md` files into `src/content/blog/`, images into `src/assets/uploads/` (adjust paths referenced in each post).
4. Commit and push — site rebuilds with the migrated posts.

Multiple authors: the script preserves the author name per post in frontmatter (`author` field already in the schema here); no user-account migration needed since there's no login system — everyone authenticates as themselves via their own GitHub account.

## Comments

Two layers, both wired up already (`src/components/Comments.astro`):

1. **Old WordPress comments** — `scripts/import_wp_post.py` fetches `/wp-json/wp/v2/comments?post=<id>` at import time and bakes them into the post's `comments:` frontmatter (author, date, content). They render as a static, read-only "Comments (N)" list — there's no backend to make them interactive, but the history isn't lost.
2. **New comments going forward** — [giscus](https://giscus.app) (GitHub Discussions-backed, free, fits since the CMS already uses GitHub). To activate:
   1. Enable Discussions on the GitHub repo (Settings → Features → Discussions).
   2. Go to https://giscus.app, fill in the repo, pick mapping "pathname", category "Comments" (create it first in Discussions) — it generates the exact `data-repo-id` / `data-category-id` values.
   3. Paste those into `src/components/Comments.astro` (replace `YOUR_GH_USERNAME/YOUR_REPO_NAME`, `REPLACE_WITH_REPO_ID`, `REPLACE_WITH_CATEGORY_ID`).
   Until configured, the widget just shows "giscus is not installed on this repository" — harmless.

## Featured image

WordPress's REST API exposes a `featured_media` ID per post, but on ayunovanti.com the `/wp-json/wp/v2/media` endpoint itself is broken (empty list, "Invalid post ID" on direct lookup) — so the featured image can't be resolved through the API for this site. `scripts/import_wp_post.py` falls back to using the **first in-article image** as `featuredImage` in frontmatter, which the post page renders as a banner above the title. If a future source site's media endpoint actually works, swap in `post._embedded['wp:featuredmedia'][0].source_url` instead.

skipped: preview/staging branch deploys — Cloudflare Pages already gives you one free per branch/PR automatically, no extra setup.
