# Agent-Ready Web Profile adoption

Start with the repository's governing instructions and `.arwp/adoption.json`. This is a publisher-authored adoption contract, not a ranking certification.

Audience: Business-rule owners and engineers reviewing spreadsheet decisions. Useful action: Validate a sample decision table and inspect its explainability trace.

## Sources and publication

- Canonical publication: https://dkharlanau.github.io/decision-tables-as-code/
- Profile source: `docs/ai/site-profile.json`; public location: `ai/site-profile.json` under the canonical site base.
- Authoritative site source: `docs`.
- Published directory: `_site`.
- Build evidence: `.github/workflows/product-pages.yml`.
- Product claims are bounded by `README.md`, `docs/agent-manifest.json`; CLI or source availability does not imply a hosted agent endpoint.

## Editorial experiment

Compare manual spreadsheet review with explicit hit-policy validation using a conflicting boundary case.

Reuse the existing intent owner before adding a page. Put the direct answer, concrete example, sources and strongest limitation in visible HTML. Keep comparison criteria symmetric; state where another approach is a better fit. Label synthetic fixtures and first-party interpretations.

The tactic IDs in the adoption contract resolve against [the ARWP corpus](https://github.com/dkharlanau/agent-ready-web-profile/blob/main/knowledge/discoverability-corpus.json). New tactics require evidence and a measurable product consequence.

## Validation and baseline

Validate the profile against [the ARWP v0.1 schema](https://github.com/dkharlanau/agent-ready-web-profile/blob/main/schema/site-profile.schema.json). For generated project sites, run `node scripts/stage-arwp.mjs <published-directory>` after building; the Pages workflow stages the same profile and discovery link into its artifact.

Check the exact emitted JSON and HTML before release. After an authorized release, verify the canonical live URL, HTTP status, profile link and response body. Record crawl eligibility, index status, search clicks/impressions, useful-action completion and independent AI citation separately. Missing observations remain unavailable; no score is a ranking promise.

This application is local only. Existing unrelated changes, product telemetry constraints and publication approvals remain in force.
