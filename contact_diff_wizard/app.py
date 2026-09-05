"""Streamlit entry point.

Run with:  streamlit run contact_diff_wizard/app.py

This is the MVP shell: language switch + connect buttons + a (not yet wired)
compare action. The OAuth flows and the matching engine are filled in in later
steps.
"""

from __future__ import annotations

import streamlit as st

from contact_diff_wizard import i18n
from contact_diff_wizard.config import load as load_config


def main() -> None:
    cfg = load_config()

    st.set_page_config(page_title="ContactDiffWizard", page_icon="🧭")

    # --- language switch ---------------------------------------------------
    default_lang = cfg.get("app", {}).get("default_language", "de")
    lang = st.sidebar.selectbox(
        i18n.t("language.label"),
        options=list(i18n.AVAILABLE),
        index=list(i18n.AVAILABLE).index(default_lang) if default_lang in i18n.AVAILABLE else 0,
        format_func=i18n.language_name,
    )
    i18n.set_language(lang)

    # --- header ----------------------------------------------------------
    st.title(i18n.t("app.title"))
    st.caption(i18n.t("app.subtitle"))

    # --- connections (stubbed) -----------------------------------------
    col_g, col_m = st.columns(2)
    with col_g:
        st.subheader("Gmail")
        st.button(i18n.t("auth.google.connect"), disabled=True)
        st.caption(i18n.t("auth.not_connected"))
    with col_m:
        st.subheader("Outlook")
        st.button(i18n.t("auth.microsoft.connect"), disabled=True)
        st.caption(i18n.t("auth.not_connected"))

    st.divider()
    st.button(i18n.t("compare.run"), disabled=True)
    st.info("MVP scaffold — OAuth and comparison are implemented in later steps.")


if __name__ == "__main__":
    main()
