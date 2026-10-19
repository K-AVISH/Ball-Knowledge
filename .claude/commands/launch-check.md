---
description: Audit LAUNCH_CHECKLIST.md against the real project state before any launch
---

Check each item in `LAUNCH_CHECKLIST.md` against the actual project, then report a table of item, real status and evidence. Do not trust the checklist's own status column.

1. Favicon: `config.FAVICON_PATH` exists, is a square PNG, and `app.py` passes it as `page_icon`.
2. No "Made with AI" or similar tags: search the code and rendered pages for attribution strings, and confirm the Streamlit footer and Deploy button are hidden.
3. Privacy policy and terms pages: both are in the navigation in `app.py`, and `OPERATOR_NAME` and `CONTACT_EMAIL` in `config.py` are set. If they are empty, the pages still show a warning banner, so the site is not ready.
4. Custom domain: not something the code can show. Ask the user for the domain and hosting setup instead of assuming.
5. Legal accuracy: compare `views/privacy.py` with what the code now stores and sends over the network, and flag anything out of date.

End with a clear yes or no on whether launch is allowed. It is allowed only when every item is done.
