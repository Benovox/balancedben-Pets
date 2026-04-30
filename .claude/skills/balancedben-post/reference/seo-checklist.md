# SEO checklist — run before shipping a post

Quick pre-publish pass. Don't ship until each box is checked.

## On-page

- [ ] `<title>` ≤ 60 chars, includes primary keyword, ends with `| Paws & Whiskers`
- [ ] `<meta name="description">` 140–160 chars, action-oriented, includes primary keyword once
- [ ] `<link rel="canonical">` points to the real published URL (https, no trailing slash mismatch)
- [ ] `<h1>` appears exactly once, matches or closely mirrors the `<title>`
- [ ] Primary keyword in first 100 words of body
- [ ] 5–8 `<h2>` sections, each with a secondary keyword where natural
- [ ] At least 3 internal links to other `post-*.html` files
- [ ] At least 1 outbound authority link (e.g. AVMA, ASPCA, AKC) where relevant
- [ ] Image `alt` text on every `<img>`, descriptive (not keyword-stuffed)
- [ ] Hero image `<meta property="og:image">` matches the visible hero

## Structured data

- [ ] JSON-LD `@type: Article` block populated with real `datePublished` + `dateModified`
- [ ] `author.name` = "Breno Leite", `publisher.name` = "Paws & Whiskers"
- [ ] `mainEntityOfPage.@id` matches canonical URL

## Affiliate + compliance

- [ ] `<p class="disclosure">` present above the fold
- [ ] Every affiliate `<a>` uses `rel="sponsored noopener"` (or `rel="nofollow sponsored"`)
- [ ] No medical claims presented as fact — frame as general info, recommend vet consult for health topics
- [ ] No stock photo credits missing where required (Pexels is license-free but attribute if requested)

## Site integration

- [ ] Added a tile/link on `blog.html`
- [ ] Added URL to `sitemap.xml` with today's `<lastmod>`
- [ ] Previous post's "Next post" link updated to point here (if maintaining chain)
- [ ] Opened the post in a browser locally, verified:
  - carousel arrows work
  - YouTube embed loads
  - Google Translate dropdown renders
  - AdSense doesn't break layout on mobile

## Performance quick check

- [ ] All `<img>` have `loading="lazy"` and `decoding="async"` (except possibly the hero)
- [ ] No inline base64 images (should be external URLs)
- [ ] Page size under ~200 KB of HTML (body text only)
