---
name: balancedben-post
description: Scaffold a new Paws & Whiskers blog post for balancedben.com. Use when the user asks to draft a new post, create a blog article, write a pet guide, or add a new post-*.html file to the site. Triggers on phrases like "new blog post", "write a post about", "draft an article on", or any request to produce a post in Breno's pet-blog template.
---

# balancedben-post

Scaffolds a ready-to-ship blog post for balancedben.com (Paws & Whiskers) matching the existing site template — SEO metadata, hero, body sections, carousel, affiliate disclosure, featured YouTube card, related reading, author box, post nav, footer.

## AdSense-review mode (DEFAULT until user says otherwise)

The site is waiting for Google AdSense approval. Until the user explicitly says "AdSense is approved":

- **NO affiliate links.** Do not insert `<a rel="sponsored">` blocks, product recommendations with commercial intent, or callouts that read like ads.
- **NO "buy this" / "shop our picks" / "recommended products" sections.**
- Keep the existing AdSense `<script>` in the head (it's required for review), but don't add ad slots inside the content.
- Skip the "Affiliate angle" input entirely.
- Focus the post on high-quality, original, helpful content — that's what AdSense reviewers reward.

When the user confirms AdSense is approved, re-enable the affiliate workflow (step 5 of Inputs below and the affiliate block in the body).

## Brainstorm-first workflow

Do NOT write a post on first turn. Always brainstorm first:

1. User gives a rough topic or goal.
2. Respond with **3–5 angles** for the topic, each with: working title, hook/why-it-goes-viral, rough outline (3–5 h2 headings), primary keyword. Keep this output compact — no full paragraphs yet.
3. User picks one angle or asks for more.
4. THEN gather the inputs below and write the post.

## Inputs to gather (after angle is picked)

Ask the user in ONE message (use AskUserQuestion if available):

1. **Final title** — confirm or adjust working title
2. **Primary keyword + 4–6 secondary keywords** — for SEO + meta keywords tag
3. **Target read length** — short (8–12 min), standard (15–20 min), deep (25+ min)
4. **Hero image URL** — Pexels URL preferred. If user has none, suggest 2–3 pexels.com search queries.
5. **Affiliate angle** — SKIP this if AdSense-review mode is on (default).
6. **2–4 related posts** — pick from `blog.html` or offer matches based on topic.
7. **YouTube video ID** (optional) — for the featured video card. Skip section if absent.

If the user gives a topic with no other details, infer reasonable defaults and confirm before writing.

## Workflow

1. Read `template.html` (lives beside this file) — it is the canonical scaffold with `{{PLACEHOLDER}}` tokens.
2. Fill every `{{...}}` placeholder. Do NOT leave any placeholder in the final file.
3. Body sections: generate 5–8 `<h2>` sections for standard length, more for deep. Each section gets 2–4 `<p>` paragraphs. Use `<table class="timeline-table">` where comparisons help, `<div class="callout">` for tips, `<div class="warning">` for cautions, `<div class="check">` for confirmations, `<blockquote>` for a single highlight quote near the top.
4. Carousel: include 4 slides with Pexels images the user provides OR ask for them. Use the exact `.carousel-wrap` structure in the template.
5. Affiliate blocks: for each affiliate category, insert a `<div class="callout">` with a short recommendation and one `<a href="#" rel="sponsored noopener">` placeholder link. Tell the user which links to swap in.
6. Related Reading: 3–4 links to existing posts — pull real filenames from the directory, never invent.
7. Filename: `post-{slug}.html` where slug is kebab-case of the title.
8. Write file to the blog root (same folder as other `post-*.html` files), not a subfolder.

## Token-efficiency rules

- NEVER dump the full body of existing posts into context. Only read `template.html` + `blog.html` (for related-post filenames) + this file.
- Do NOT read other `post-*.html` files unless the user explicitly asks to mirror one.
- Write the new post in a single Write call — do not chunk into many Edits.
- Keep this SKILL.md short; push boilerplate into `template.html` and `reference/` files.

## Constants (do not ask the user — these are fixed for this site)

- Site: Paws & Whiskers — https://balancedben.com
- Author: Breno Leite
- GA4 ID: G-3GJCMZ6Y2E
- AdSense publisher: ca-pub-4953485482546252
- YouTube channel: https://www.youtube.com/@BalancedPets
- Palette: teal `#2EC4B6` primary, coral `#FF6B6B` secondary, dark `#2F3E46`, light `#FAF3E0`
- Fonts: Poppins (headings), Inter (body)
- Every post links `visual-polish.css` after inline `<style>`.
- Every post includes the carousel `<script>` block at the end of `<body>` (copy verbatim from template).
- Every post includes Google Translate block (copy verbatim from template).

## After writing

Report to the user:
- Filename created
- Word count estimate
- List of `{{PLACEHOLDER}}` locations if any were intentionally left (should be zero)
- Specific affiliate links they still need to swap in (real URLs)
- Reminder to add the new post to `blog.html` and `sitemap.xml`

## See also

- `template.html` — scaffold with placeholders
- `reference/seo-checklist.md` — quick SEO pass before shipping
