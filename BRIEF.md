# Brief: public NCD grading framework

Owner request (MT, 2026-10-14): publish our NCD/app grading framework as a standalone Markdown file any external AI model (ChatGPT, Claude, Gemini) can fetch and apply, so the owner can paste one link plus "grade this project".

Requirements:
- `NCD-GRADING-FRAMEWORK.md`: self-contained; dimensions and weights; 0-10 anchors (5, 7, 8.5, 10); critical-finding rules; pass gates (overall 8.5, no dimension below 7, zero criticals, 9.0 = excellent); Website NCD and App/Build profiles incl. zero-figuring-out usability scoring; evidence checklist; exact output JSON schema and Markdown scorecard; anti-inflation rules; grader instructions at top.
- `GRADE-DCN.md`: ready prompt for the DCN preview (/, /directory/, /career/); repo is private.
- Hosted as plain public pages (raw .md served as text/plain with CORS, plus an HTML view) on the empty default site of Firebase project `dc-trades-network`, path /grading/. Content is not sensitive.
- No scripts, forms, tracking or personal data on the pages.
