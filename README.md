# ContactDiffWizard

Compare the contacts in your **Outlook** account (Microsoft Graph) and your
**Gmail** account (Google People API) and see the differences at a glance:

- contacts that exist **only in Outlook**
- contacts that exist **only in Gmail**
- contacts that exist in **both but with differing fields** (phone, email, address, …)

The MVP is **read-only**: it compares and displays. It does **not** write, merge
or sync anything.

> **Status:** early scaffold. OAuth login and the comparison engine are not
> wired up yet.

## How it works

You do **not** need to register anything with Google or Microsoft. The project
ships with a single OAuth client registration; when you start the app you just
log in through the normal Google / Microsoft consent screen in your browser.

While the Google app is unverified you will see a "Google hasn't verified this
app" warning — click *Advanced → Go to ContactDiffWizard* to continue. Only
read-only contact scopes are requested (`contacts.readonly`, `Contacts.Read`).

## Requirements

- Python 3.11+

## Setup

```bash
git clone https://github.com/menderle75/contact-diff-wizard.git
cd contact-diff-wizard
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.toml config.toml   # client IDs will be filled in here
```

## Run

```bash
streamlit run contact_diff_wizard/app.py
```

## Language

The UI ships with English and German and a language switcher in the sidebar.

## Roadmap

- [ ] Google OAuth (loopback) + People API contact fetch
- [ ] Microsoft OAuth (MSAL) + Graph contact fetch
- [ ] Matching (email → phone → fuzzy name) and field-level diff
- [ ] Diff UI
- [ ] Later, out of MVP scope: iCloud / CardDAV sources, merge/sync

## License

MIT — see [LICENSE](LICENSE).
