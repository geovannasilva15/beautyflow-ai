# Public website

A static public marketing/portfolio page lives in `site/index.html`.
It does not contain customer data, admin credentials or API access.

GitHub Pages deployment uses `.github/workflows/pages.yml`.
After merging to main, the repository owner must select **Settings >
Pages > Build and deployment > Source: GitHub Actions**. Once GitHub
Pages is enabled, the workflow deploys the static site.

Expected default Pages URL after successful deployment:
https://geovannasilva15.github.io/beautyflow-ai/

This is **not** the authenticated management application. The internal
Streamlit/FastAPI dashboard still requires a secure hosting and auth strategy.
Do not expose the demo login, API or customer database publicly.
