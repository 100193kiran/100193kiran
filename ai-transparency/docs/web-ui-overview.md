# Webpage (HTML/CSS) Overview

## Pages
- `/` home page with model id search field.
- `/models/[id]` model detail page with trust score, benchmark summary, and review form.

## HTML structure (conceptual)
- `<main>` root container
- `<h1>/<h2>` titles
- `<input>` fields for model search/review form
- `<button>` actions
- `<pre>` benchmark JSON block

## CSS/layout approach
- Current implementation uses inline styles for speed:
  - root content padding
  - simple single-column layout
- Recommended next step:
  - migrate to CSS modules or Tailwind
  - design tokens for spacing/colors/typography
  - component-level responsiveness
