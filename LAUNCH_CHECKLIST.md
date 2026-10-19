# Launch checklist

The site is not to be launched until every item below is done.

| Item | Status | Notes |
|---|---|---|
| Favicon | Done | `assets/favicon.png`, set in `app.py` through `config.FAVICON_PATH`. Replace the file to change it. |
| No "Made with AI" or similar tags | Done | Streamlit's footer and Deploy button are hidden in `ui.py`. A test scans the code for attribution strings. Check the hosting platform does not add its own badge. |
| Privacy policy page | Drafted, needs your input | `views/privacy.py`. Set `OPERATOR_NAME` and `CONTACT_EMAIL` in `config.py`. Have a qualified person review it before launch. |
| Terms and conditions page | Drafted, needs your input | `views/terms.py`. Same settings, plus `GOVERNING_LAW` if you want that clause. Have it reviewed too. |
| Custom domain | Not done | Needs a domain, hosting, and HTTPS (browsers only allow camera access on HTTPS or localhost). Video over the internet usually also needs a TURN server for WebRTC. |

Also before launch:

- Re-read both legal pages after each new feature (training, meme upload) and update them if data handling changes.
- Re-test the camera on the final domain, on Chrome and Safari.
- The legal pages show a warning banner until the operator details are set. Launch only when that banner is gone.

Design rules (enforced by `tests/test_style_rules.py`): no emoji, no em dashes, no gradients, no animations, no pill shapes, no purple, no fake metrics, no stock or AI-generated imagery.
