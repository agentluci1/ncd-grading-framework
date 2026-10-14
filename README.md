# NCD grading framework site

Public, non-sensitive rubric for external AI graders. Served at https://dc-trades-network.web.app/grading/ (default site of Firebase project `dc-trades-network`, hosting target `grading`).

- Sources of truth: `public/grading/NCD-GRADING-FRAMEWORK.md` and `public/grading/GRADE-DCN.md`. Never hand-edit the `.html` files.
- Setup: `pip install "markdown==3.10.2" "jsonschema>=4.19"` (markdown is pinned so generated HTML is byte-stable; jsonschema is for tests).
- Regenerate HTML: `python3 build.py` (renders all pages first; on any write error restores every original output, prints the error and any unrestored path, exits 1).
- Validate: `python3 -m unittest discover -s tests` (schema is valid JSON Schema, example scorecard validates, weights/gate arithmetic, HTML in sync, lists render).
- View locally: `python3 -m http.server -d public 8000` then open http://localhost:8000/grading/
- Target mapping: `.firebaserc` (copy kept visible as `firebaserc.json`) maps target `grading` to site `dc-trades-network` in project `dc-trades-network`. On a fresh checkout: `cp firebaserc.json .firebaserc`.
- Deploy (luci@ account, through shipgate): `firebase deploy --only hosting:grading --account luci@agentluci.com`
