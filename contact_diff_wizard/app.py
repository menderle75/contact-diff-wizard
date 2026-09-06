"""Streamlit entry point.

    streamlit run contact_diff_wizard/app.py

One central view; a selector at the top switches between the four categories.
Below it: a one-row-per-contact list on the left, a side-by-side Gmail/Outlook
comparison on the right for the selected contact.
"""

from __future__ import annotations

import html
import os
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
LEFT_LABEL = "Gmail"
RIGHT_LABEL = "Outlook"

_DETAIL_CSS = """
<style>
.cdw-cmp { overflow-x:auto; }
.cdw-cmp table { width:100%; border-collapse:collapse; font-size:0.9rem;
  table-layout:fixed; min-width:420px; }
.cdw-cmp col.k { width:120px; }
.cdw-cmp th, .cdw-cmp td { padding:6px 10px; text-align:left; vertical-align:top;
  border-bottom:1px solid rgba(128,128,128,0.25); word-break:break-word; }
.cdw-cmp th { font-weight:600; opacity:0.7; }
.cdw-cmp td.k { white-space:normal; font-weight:600; }
.cdw-cmp tr.diff td { background:rgba(255,196,0,0.16); }
.cdw-cmp tr.diff td.k { background:rgba(255,196,0,0.30); }
.cdw-cmp .muted td { opacity:0.65; }
.cdw-cmp details { margin-top:10px; }
.cdw-cmp summary { cursor:pointer; opacity:0.85; font-size:0.9rem; padding:4px 0; }
.cdw-cmp .missing { opacity:0.4; }
</style>
"""


def _google_source(cfg: dict) -> GoogleContactSource:
    g = cfg["google"]
    return GoogleContactSource(
        client_id=g["client_id"],
        client_secret=g["client_secret"],
        scopes=g["scopes"],
        token_path=TOKEN_PATH,
    )


# ---------------------------------------------------------------------------
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

    upload = st.sidebar.file_uploader(
        i18n.t("upload.label"), type=["csv", "vcf", "txt"], help=i18n.t("upload.help")
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

    # dev convenience: CDW_DEV_OUTLOOK=path/to/export.csv preloads the file so
    # the compare button works without a manual upload. No effect when unset.
    dev_file = os.environ.get("CDW_DEV_OUTLOOK")
    if dev_file and not st.session_state.get("outlook_bytes") and Path(dev_file).is_file():
        st.session_state.outlook_bytes = Path(dev_file).read_bytes()
        st.session_state.outlook_name = Path(dev_file).name
        st.sidebar.caption(f"dev: {Path(dev_file).name}")

    ready = connected and st.session_state.get("outlook_bytes")
    if st.sidebar.button(i18n.t("compare.run"), type="primary", disabled=not ready):
        with st.spinner(i18n.t("compare.running")):
            google = _google_source(cfg)
            google.authenticate()
            outlook = OutlookFileContactSource.from_upload(
                st.session_state.outlook_bytes, st.session_state.outlook_name
            )
            st.session_state.groups = compare([google, outlook])
            st.session_state.pop("sel_idx", None)
            st.session_state.pop("decisions_seed", None)
        st.toast(i18n.t("results.updated"))
    if not ready:
        st.sidebar.caption(i18n.t("compare.needs_both"))


# ---------------------------------------------------------------------------
def _vals_html(vals: list[str]) -> str:
    if not vals:
        return "<span class='missing'>—</span>"
    return "<br>".join(html.escape(v) for v in vals)


def _detail_html(cmp: dict) -> str:
    cols = "<colgroup><col class='k'><col><col></colgroup>"
    rows = []
    rows.append(
        f"<tr><th></th><th>{LEFT_LABEL}</th><th>{RIGHT_LABEL}</th></tr>"
    )
    for r in cmp["diff_rows"]:
        rows.append(
            f"<tr class='diff'><td class='k'>{r['icon']} {html.escape(r['label'])}</td>"
            f"<td>{_vals_html(r['left'])}</td><td>{_vals_html(r['right'])}</td></tr>"
        )
    if not cmp["diff_rows"]:
        rows.append(
            "<tr class='muted'><td class='k'>—</td><td colspan='2'>"
            f"{html.escape(i18n.t('detail.no_diff'))}</td></tr>"
        )
    table = f"<div class='cdw-cmp'><table>{cols}{''.join(rows)}</table>"

    if cmp["same_rows"]:
        same = [
            f"<tr class='muted'><td class='k'>{r['icon']} {html.escape(r['label'])}</td>"
            f"<td>{_vals_html(r['left'])}</td><td>{_vals_html(r['right'])}</td></tr>"
            for r in cmp["same_rows"]
        ]
        table += (
            f"<details><summary>{i18n.t('detail.same_count', n=len(cmp['same_rows']))}"
            f"</summary><table>{cols}{''.join(same)}</table></details>"
        )
    return _DETAIL_CSS + table + "</div>"


def _decision_panel(idx: int, cmp: dict) -> None:
    if cmp["category"].value != "diverging" or not cmp["diff_rows"]:
        return
    st.markdown(f"**{i18n.t('decide.title')}**")
    opts = ["offen", LEFT_LABEL, RIGHT_LABEL, i18n.t("decide.both")]
    for r in cmp["diff_rows"]:
        st.radio(
            f"{r['icon']} {r['label']}",
            options=opts,
            horizontal=True,
            key=f"dec::{idx}::{r['field']}",
        )


def _collect_decisions(groups) -> list[dict]:
    out = []
    for key, val in st.session_state.items():
        if not key.startswith("dec::") or val == "offen":
            continue
        _, sidx, field = key.split("::", 2)
        g = groups[int(sidx)]
        cmp = report.comparison(g)
        row = next((x for x in cmp["diff_rows"] if x["field"] == field), None)
        if row is None:
            continue
        out.append({
            "Kontakt": cmp["name"],
            "Feld": row["label"],
            "Entscheidung": val,
            "Wert Gmail": " | ".join(row["left"]),
            "Wert Outlook": " | ".join(row["right"]),
        })
    out.sort(key=lambda r: (r["Kontakt"].casefold(), r["Feld"]))
    return out


# ---------------------------------------------------------------------------
def _results() -> None:
    groups = st.session_state.get("groups")
    if not groups:
        st.info(i18n.t("results.none"))
        return

    counts = report.category_counts(groups)
    labelled = {
        "view.only_google": counts["only_google"],
        "view.only_outlook": counts["only_outlook"],
        "view.identical": counts["identical"],
        "view.diverging": counts["diverging"],
    }
    choice = st.segmented_control(
        i18n.t("view.label"),
        options=list(labelled),
        format_func=lambda k: f"{i18n.t(k)} · {labelled[k]}",
        default="view.diverging",
        key="view_choice",
    ) or "view.diverging"

    query = st.text_input(i18n.t("filter.label"), "").strip().casefold()

    indexed = [
        (i, g) for i, g in enumerate(groups)
        if report.in_category(g, choice)
        and (not query or query in next(
            (c.display_name for c in g.members if c.display_name), ""
        ).casefold())
    ]
    rows = report.master_rows(indexed, choice)
    idx_by_pos = [r["_idx"] for r in rows]
    display_rows = [{k: v for k, v in r.items() if k != "_idx"} for r in rows]

    st.caption(i18n.t("table.count", n=len(rows)))
    if not rows:
        st.info(i18n.t("table.empty"))
        return

    list_col, detail_col = st.columns([0.85, 1.3], gap="medium")

    with list_col:
        col_cfg = {
            "Δ": st.column_config.TextColumn("Δ", width="small",
                                             help=i18n.t("col.delta_help")),
            "#": st.column_config.NumberColumn("#", width="small"),
        }
        event = st.dataframe(
            display_rows,
            use_container_width=True,
            hide_index=True,
            height=min(70 + 35 * len(display_rows), 620),
            on_select="rerun",
            selection_mode="single-row",
            column_config=col_cfg,
            key=f"master::{choice}",
        )
        picked = event.selection["rows"] if event and event.selection else []
        pos = picked[0] if picked else 0
        sel_idx = idx_by_pos[pos]

    with detail_col:
        g = groups[sel_idx]
        cmp = report.comparison(g)
        st.markdown(f"### {cmp['name']}")
        if len(g.source_ids) > 1:
            st.caption(i18n.t("detail.matched_by", reason=cmp["match_reason"] or "—"))
        st.markdown(_detail_html(cmp), unsafe_allow_html=True)
        _decision_panel(sel_idx, cmp)

    made = _collect_decisions(groups)
    if made:
        st.divider()
        st.download_button(
            i18n.t("decide.export", n=len(made)),
            data=report.decisions_csv(made),
            file_name="contactdiffwizard-entscheidungen.csv",
            mime="text/csv",
        )


# ---------------------------------------------------------------------------
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
