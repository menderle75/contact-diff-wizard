# ContactDiffWizard

Compare the contacts in your **Outlook** account and your **Gmail** account
(Google People API) and see the differences at a glance:

- contacts that exist **only in Outlook**
- contacts that exist **only in Gmail**
- contacts that exist in **both but with differing fields** (phone, email, address, …)

The MVP is **read-only**: it compares and displays. It does **not** write, merge
or sync anything.

> **Status:** early. Gmail login + fetch works. Outlook is read from an exported
> file. Matching engine and UI are in progress.

## How it works

**Gmail:** you log in through the normal Google consent screen in your browser
(no API setup on your side). While the app is unverified you'll see a "Google
hasn't verified this app" warning — click *Advanced → Go to ContactDiffWizard*.
Only the read-only `contacts.readonly` scope is requested.

**Outlook:** export your contacts to a file and hand that file to the app —
there is no Microsoft/Azure setup. Supported:

- **CSV** — Outlook.com: *People → Manage → Export contacts*; or classic Outlook
  Desktop: *File → Open & Export → Import/Export → Export to a file → Comma
  Separated Values*.
- **vCard** (`.vcf`) — one or many cards.

## Requirements

- Python 3.11+

## Setup

```bash
git clone https://github.com/menderle75/contact-diff-wizard.git
cd contact-diff-wizard
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.toml config.toml   # Google client id/secret go here
```

## Run

```bash
streamlit run contact_diff_wizard/app.py
```

## Language

The UI ships with English and German and a language switcher in the sidebar.

## Roadmap

- [x] Google OAuth (loopback) + People API contact fetch
- [x] Outlook export parser (CSV + vCard)
- [x] Matching (email → phone → fuzzy name) and field-level diff
- [x] Diff UI (one view, category selector)
- [ ] Duplicate view, nicer address/phone diff rendering, full UI i18n
- [ ] Later, out of MVP scope: iCloud / CardDAV sources, Microsoft Graph, merge/sync

## License

MIT — see [LICENSE](LICENSE).
