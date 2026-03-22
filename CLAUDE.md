# CLAUDE.md

## Project Overview

NORMALAIZER is an AI-powered communication translation platform that bridges neurotypical and neurodivergent communication styles in real time.

## Tech Stack

- **Backend**: Python/Flask
- **Frontend**: Tailwind CSS, Alpine.js
- **Templates**: Jinja2

## Structure

- `backend/` - Flask application code
- `backend/app/templates/` - Jinja2 HTML templates
- `backend/app/templates/pages/` - Page-level templates (landing, dashboard, etc.)
- `backend/app/templates/partials/` - Reusable template partials

## Development Rules

- Do not add AI provider attribution (e.g., "Powered by [provider]") in user-facing UI.
- Do not add co-author lines or AI attribution to git commits.
- Keep landing page copy focused on product capabilities, not implementation details.
