"""Streamlit entry point.

    streamlit run contact_diff_wizard/app.py

One central view; a selector at the top switches between the four categories.
Sources are configured in the sidebar (Gmail via OAuth, Outlook via file upload).
"""

from __future__ import annotations

import sys
from pathlib import Path

# `streamlit run contact_diff_wizard/app.py` puts this file's directory on
# sys.path, not the repo root — make the package importable either way.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st  # noqa: E402

from contact_diff_wizard import i18n, report  # noqa: E402
from contact_diff_wizard.config import load as load_config  # noqa: E402
from contact_diff_wizard.matching.engine import compare  # noqa: E402
from contact_diff_wizard.sources.google import GoogleContactSource  # noqa: E402
from contact_diff_wizard.sources.outlook_file import (  # noqa: E402
    OutlookFileContactSource,
    parse_bytes,
)

TOKEN_PATH = "google.token.json"


def _google_source(cfg: dict) -> GoogleContactSource:
    g = cfg["google"]
    return GoogleContactSource(
        client_id=g["client_id"],
        client_secret=g["client_secret"],
        scopes=g["scopes"],
        token_path=TOKEN_PATH,
    )


def _sidebar(cfg: dict) -> None:
    st.sidebar.selectbox(
        i18n.t("language.label"),
        options=list(i18n.AVAILABLE),
        index=list(i18n.AVAILABLE).index(st.session_state.lang),
        format_func=i18n.language_name,
        key="lang",
    )
    i18n.set_language(st.session_state.lang)

    st.sidebar.header(i18n.t("sidebar.sources"))

    # --- Gmail (OAuth) ---
    connected = _google_source(cfg).is_authenticated()
    if connected:
        st.sidebar.success(i18n.t("auth.google.connected"))
    if st.sidebar.button(i18n.t("auth.google.connect"), disabled=connected):
        try:
            with st.spinner(i18n.t("auth.google.connecting")):
                _google_source(cfg).authenticate()
            st.rerun()
        except Exception as exc:  # noqa: BLE001 - surface any login failure
            st.sidebar.error(i18n.t("auth.google.error", error=str(exc)))

    # --- Outlook (file) ---
    upload = st.sidebar.file_uploader(
        i18n.t("upload.label"),
        type=["csv", "vcf", "txt"],
        help=i18n.t("upload.help"),
    )
    if upload is not None:
        data = upload.getvalue()
        st.session_state.outlook_bytes = data
        st.session_state.outlook_name = upload.name
        try:
            n = len(parse_bytes(data, filename=upload.name))
            st.sidebar.caption(i18n.t("upload.loaded", n=n))
        except Exception as exc:  # noqa: BLE001
            st.sidebar.error(str(exc))

    # --- run ---
    ready = connected and st.session_state.get("outlook_bytes")
    if st.sidebar.button(i18n.t("compare.run"), type="primary", disabled=not ready):
        with st.spinner(i18n.t("compare.running")):
            google = _google_source(cfg)
            google.authenticate()
            outlook = OutlookFileContactSource.from_upload(
                st.session_state.outlook_bytes, st.session_state.outlook_name
            )
            st.session_state.groups = compare([google, outlook])
        st.toast(i18n.t("results.updated"))
    if not ready:
        st.sidebar.caption(i18n.t("compare.needs_both"))


def _results() -> None:
    groups = st.session_state.get("groups")
    if not groups:
        st.info(i18n.t("results.none"))
        return

    counts = report.category_counts(groups)
    options = {
        "view.only_google": counts["only_google"],
        "view.only_outlook": counts["only_outlook"],
        "view.identical": counts["identical"],
        "view.diverging": counts["diverging"],
    }
    choice = st.segmented_control(
        i18n.t("view.label"),
        options=list(options),
        format_func=lambda k: f"{i18n.t(k)} ({options[k]})",
        default="view.diverging",
        key="view_choice",
    ) or "view.diverging"

    query = st.text_input(i18n.t("filter.label"), "").strip().casefold()

    if choice == "view.only_google":
        rows = report.only_in(groups, "google")
        name_key = "Name"
    elif choice == "view.only_outlook":
        rows = report.only_in(groups, "outlook")
        name_key = "Name"
    elif choice == "view.identical":
        rows = report.identical(groups)
        name_key = "Name"
    else:
        rows = report.diverging_rows(groups)
        name_key = "Kontakt"

    if query:
        rows = [r for r in rows if query in r.get(name_key, "").casefold()]

    st.caption(i18n.t("table.count", n=len(rows)))
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info(i18n.t("table.empty"))


def main() -> None:
    st.set_page_config(page_title="ContactDiffWizard", page_icon="🧭", layout="wide")
    cfg = load_config()
    st.session_state.setdefault("lang", cfg.get("app", {}).get("default_language", "de"))
    i18n.set_language(st.session_state.lang)

    _sidebar(cfg)

    st.title(i18n.t("app.title"))
    st.caption(i18n.t("app.subtitle"))
    _results()


if __name__ == "__main__":
    main()
