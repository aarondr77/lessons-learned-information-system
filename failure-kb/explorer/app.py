#!/usr/bin/env python3
"""Dash explorer for the NASA LLIS failure knowledge base."""

from __future__ import annotations

import sys
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, dash_table, dcc, html

EXPLORER_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(EXPLORER_ROOT))

from data_loader import (  # noqa: E402
    apply_filters,
    explode_for_export,
    load_dataframe,
    load_taxonomy_labels,
    pattern_agent_matrix,
)

AGENT_LABELS, PATTERN_LABELS = load_taxonomy_labels()
DF, DATA_SOURCE = load_dataframe()
HAS_CLASSIFICATION = "primary_agent" in DF.columns and DF["primary_agent"].notna().any()

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="LLIS Failure Knowledge Base",
)

FILTER_IDS = [
    "filter-agents",
    "filter-patterns",
    "filter-orgs",
    "filter-topics",
    "filter-phases",
    "filter-confidence",
    "filter-impact",
    "filter-date-start",
    "filter-date-end",
    "filter-search",
]
FILTER_INPUTS = [Input(fid, "value") for fid in FILTER_IDS]


def _options(series: pd.Series) -> list[dict]:
    values = sorted(v for v in series.dropna().unique() if str(v).strip())
    return [{"label": str(v), "value": v} for v in values]


def _labeled_options(ids: list[str], label_map: dict[str, str]) -> list[dict]:
    return [{"label": label_map.get(i, i), "value": i} for i in sorted(ids)]


def _topic_options(df: pd.DataFrame) -> list[dict]:
    topics: set[str] = set()
    for items in df.get("nasa_topics", pd.Series(dtype=object)):
        for items_list in [items]:
            if not items_list:
                continue
            for t in items_list:
                if t and t != "None":
                    topics.add(t)
    return [{"label": t, "value": t} for t in sorted(topics)]


def filter_panel() -> dbc.Card:
    return dbc.Card(
        dbc.CardBody([
            html.H5("Filters", className="card-title"),
            dbc.Label("Search"),
            dbc.Input(id="filter-search", type="text", placeholder="Title or abstract…", debounce=True),
            dbc.Label("Primary / secondary agent", className="mt-2"),
            dcc.Dropdown(id="filter-agents", multi=True, placeholder="All agents"),
            dbc.Label("Failure pattern", className="mt-2"),
            dcc.Dropdown(id="filter-patterns", multi=True, placeholder="All patterns"),
            dbc.Label("Organization", className="mt-2"),
            dcc.Dropdown(id="filter-orgs", multi=True, placeholder="All centers"),
            dbc.Label("NASA topic", className="mt-2"),
            dcc.Dropdown(id="filter-topics", multi=True, placeholder="All topics"),
            dbc.Label("Program phase", className="mt-2"),
            dcc.Dropdown(id="filter-phases", multi=True, placeholder="All phases"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Confidence", className="mt-2"),
                    dcc.Dropdown(id="filter-confidence", multi=True, placeholder="All"),
                ], md=6),
                dbc.Col([
                    dbc.Label("Impact severity", className="mt-2"),
                    dcc.Dropdown(id="filter-impact", multi=True, placeholder="All"),
                ], md=6),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Date from", className="mt-2"),
                    dbc.Input(id="filter-date-start", type="date"),
                ], md=6),
                dbc.Col([
                    dbc.Label("Date to", className="mt-2"),
                    dbc.Input(id="filter-date-end", type="date"),
                ], md=6),
            ]),
            dbc.Button("Clear filters", id="clear-filters", color="secondary", outline=True, className="mt-3 me-2"),
            dbc.Button("Export CSV", id="export-btn", color="primary", className="mt-3"),
        ]),
        className="mb-3",
    )


banner = dbc.Alert(
    [
        html.Strong("Classification pending. "),
        f"Showing raw lessons from {DATA_SOURCE}. ",
        "Run classify_lessons.py then build_knowledge_base.py for full analytics.",
    ],
    color="warning",
    className="mb-3",
) if not HAS_CLASSIFICATION else html.Div()

app.layout = dbc.Container([
    html.H1("NASA LLIS Failure Knowledge Base", className="mt-3 mb-1"),
    html.P(f"Data source: {DATA_SOURCE} · {len(DF):,} lessons", className="text-muted"),
    banner,
    dbc.Row([
        dbc.Col(filter_panel(), md=3),
        dbc.Col([
            dbc.Tabs([
                dbc.Tab(label="Dashboard", tab_id="tab-dashboard"),
                dbc.Tab(label="Top issues", tab_id="tab-issues"),
                dbc.Tab(label="Browse lessons", tab_id="tab-browse"),
            ], id="tabs", active_tab="tab-dashboard", className="mb-3"),
            html.Div(id="panel-dashboard"),
            html.Div(id="panel-issues", style={"display": "none"}),
            html.Div(id="panel-browse", style={"display": "none"}, children=[
                html.P(id="browse-count", className="text-muted"),
                dash_table.DataTable(
                    id="lessons-table",
                    page_size=15,
                    row_selectable="single",
                    selected_rows=[],
                    style_table={"overflowX": "auto"},
                    style_cell={
                        "textAlign": "left",
                        "maxWidth": 260,
                        "overflow": "hidden",
                        "textOverflow": "ellipsis",
                    },
                ),
                html.Div(id="lesson-detail", className="mt-3"),
            ]),
        ], md=9),
    ]),
    dcc.Download(id="download-export"),
], fluid=True)


def _get_filtered(*filter_values):
    return apply_filters(
        DF,
        agents=filter_values[0] or None,
        patterns=filter_values[1] or None,
        organizations=filter_values[2] or None,
        topics=filter_values[3] or None,
        phases=filter_values[4] or None,
        confidences=filter_values[5] or None,
        impacts=filter_values[6] or None,
        date_start=filter_values[7],
        date_end=filter_values[8],
        search=filter_values[9],
    )


@app.callback(
    Output("filter-agents", "options"),
    Output("filter-patterns", "options"),
    Output("filter-orgs", "options"),
    Output("filter-topics", "options"),
    Output("filter-phases", "options"),
    Output("filter-confidence", "options"),
    Output("filter-impact", "options"),
    Input("tabs", "active_tab"),
)
def populate_filter_options(_tab):
    agents = (
        _labeled_options(list(AGENT_LABELS.keys()), AGENT_LABELS)
        if AGENT_LABELS
        else _options(DF.get("primary_agent", pd.Series()))
    )
    patterns = _labeled_options(list(PATTERN_LABELS.keys()), PATTERN_LABELS) if PATTERN_LABELS else []
    return (
        agents,
        patterns,
        _options(DF.get("organization", pd.Series())),
        _topic_options(DF),
        _options(DF.get("program_phase", pd.Series())),
        _options(DF.get("confidence", pd.Series())),
        _options(DF.get("impact_severity", pd.Series())),
    )


@app.callback(
    Output("filter-agents", "value"),
    Output("filter-patterns", "value"),
    Output("filter-orgs", "value"),
    Output("filter-topics", "value"),
    Output("filter-phases", "value"),
    Output("filter-confidence", "value"),
    Output("filter-impact", "value"),
    Output("filter-date-start", "value"),
    Output("filter-date-end", "value"),
    Output("filter-search", "value"),
    Input("clear-filters", "n_clicks"),
    prevent_initial_call=True,
)
def clear_filters(_n):
    return ([], [], [], [], [], [], [], None, None, "")


@app.callback(
    Output("panel-dashboard", "style"),
    Output("panel-issues", "style"),
    Output("panel-browse", "style"),
    Input("tabs", "active_tab"),
)
def toggle_panels(active_tab):
    hidden = {"display": "none"}
    shown = {"display": "block"}
    return (
        shown if active_tab == "tab-dashboard" else hidden,
        shown if active_tab == "tab-issues" else hidden,
        shown if active_tab == "tab-browse" else hidden,
    )


@app.callback(
    Output("panel-dashboard", "children"),
    *FILTER_INPUTS,
)
def update_dashboard(*filter_values):
    df = _get_filtered(*filter_values)
    charts = []

    kpi_row = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Filtered lessons", className="text-muted mb-1"),
            html.H3(f"{len(df):,}", className="mb-0"),
        ])), md=3, className="mb-3"),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Unique centers", className="text-muted mb-1"),
            html.H3(f"{df['organization'].nunique()}", className="mb-0"),
        ])), md=3, className="mb-3"),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("High / critical impact", className="text-muted mb-1"),
            html.H3(
                str(len(df[df["impact_severity"].isin(["critical", "major"])]))
                if HAS_CLASSIFICATION else "—",
                className="mb-0",
            ),
        ])), md=3, className="mb-3"),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Avg patterns / lesson", className="text-muted mb-1"),
            html.H3(
                f"{df['failure_patterns'].apply(len).mean():.1f}"
                if HAS_CLASSIFICATION and len(df) else "—",
                className="mb-0",
            ),
        ])), md=3, className="mb-3"),
    ])

    if HAS_CLASSIFICATION and not df.empty:
        agent_counts = df["primary_agent"].value_counts().reset_index()
        agent_counts.columns = ["agent", "count"]
        agent_counts["label"] = agent_counts["agent"].map(lambda a: AGENT_LABELS.get(a, a))
        charts.append(dbc.Col(dcc.Graph(figure=px.bar(
            agent_counts, x="label", y="count", title="Lessons by primary agent",
        )), md=6))

        pattern_rows = [p for patterns in df["failure_patterns"] for p in patterns]
        if pattern_rows:
            pat_df = pd.Series(pattern_rows).value_counts().head(15).reset_index()
            pat_df.columns = ["pattern", "count"]
            pat_df["label"] = pat_df["pattern"].map(lambda p: PATTERN_LABELS.get(p, p))
            charts.append(dbc.Col(dcc.Graph(figure=px.bar(
                pat_df, x="count", y="label", orientation="h", title="Top failure patterns",
            )), md=6))

        if df["impact_severity"].notna().any():
            imp = df["impact_severity"].value_counts().reset_index()
            imp.columns = ["severity", "count"]
            charts.append(dbc.Col(dcc.Graph(figure=px.pie(
                imp, names="severity", values="count", title="Impact severity",
            )), md=4))

    if not df.empty:
        org_counts = df["organization"].value_counts().head(12).reset_index()
        org_counts.columns = ["organization", "count"]
        charts.append(dbc.Col(dcc.Graph(figure=px.bar(
            org_counts, x="organization", y="count", title="Lessons by center (top 12)",
        )), md=6))

        if df["year"].notna().any():
            yearly = df.groupby("year").size().reset_index(name="count")
            charts.append(dbc.Col(dcc.Graph(figure=px.line(
                yearly, x="year", y="count", title="Lessons over time", markers=True,
            )), md=6))

    return [kpi_row, dbc.Row(charts)]


@app.callback(
    Output("panel-issues", "children"),
    *FILTER_INPUTS,
)
def update_issues(*filter_values):
    df = _get_filtered(*filter_values)
    if not HAS_CLASSIFICATION or df.empty:
        return dbc.Alert("Classification data required for top-issues analytics.", color="info")

    pattern_rows = [p for patterns in df["failure_patterns"] for p in patterns]
    pat_df = pd.Series(pattern_rows).value_counts().head(20).reset_index()
    pat_df.columns = ["pattern", "count"]
    pat_df["label"] = pat_df["pattern"].map(lambda p: PATTERN_LABELS.get(p, p))

    matrix = pattern_agent_matrix(df)
    heatmap = go.Figure(data=go.Heatmap(
        z=matrix.values,
        x=[AGENT_LABELS.get(c, c) for c in matrix.columns],
        y=[PATTERN_LABELS.get(i, i) for i in matrix.index],
        colorscale="Blues",
    ))
    heatmap.update_layout(title="Pattern × primary agent co-occurrence", height=500)

    high_impact = df[df["impact_severity"].isin(["critical", "major"])].sort_values(
        ["impact_severity", "lesson_date"], ascending=[True, False],
    )
    hi_cols = ["lesson_number", "title", "primary_agent", "impact_severity", "impact_notes", "url"]
    hi_table = dash_table.DataTable(
        columns=[{"name": c.replace("_", " ").title(), "id": c} for c in hi_cols if c in high_impact.columns],
        data=high_impact[hi_cols].head(25).to_dict("records"),
        page_size=10,
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left", "maxWidth": 280, "overflow": "hidden", "textOverflow": "ellipsis"},
    )

    return html.Div([
        dbc.Row([
            dbc.Col(dcc.Graph(figure=px.bar(
                pat_df, x="count", y="label", orientation="h", title="Most common failure patterns",
            )), md=6),
            dbc.Col(dcc.Graph(figure=heatmap), md=6),
        ]),
        html.H4("High-impact lessons", className="mt-4"),
        hi_table,
    ])


@app.callback(
    Output("lessons-table", "columns"),
    Output("lessons-table", "data"),
    Output("browse-count", "children"),
    *FILTER_INPUTS,
)
def update_browse_table(*filter_values):
    df = _get_filtered(*filter_values)
    table_cols = ["lesson_number", "title", "lesson_date", "organization", "program_phase"]
    if HAS_CLASSIFICATION:
        table_cols += ["primary_agent", "impact_severity", "confidence"]

    sorted_df = df[table_cols].sort_values("lesson_date", ascending=False, na_position="last")
    for col in sorted_df.columns:
        if col == "lesson_date":
            sorted_df[col] = sorted_df[col].dt.strftime("%Y-%m-%d").where(sorted_df[col].notna(), "")
    columns = [{"name": c.replace("_", " ").title(), "id": c} for c in table_cols]
    return columns, sorted_df.to_dict("records"), f"{len(df):,} lessons match filters"


@app.callback(
    Output("lesson-detail", "children"),
    Input("lessons-table", "selected_rows"),
    Input("lessons-table", "data"),
    *FILTER_INPUTS,
)
def show_lesson_detail(selected_rows, table_data, *filter_values):
    if not selected_rows or not table_data:
        return dbc.Alert("Select a lesson row to view details.", color="light")

    lesson_number = str(table_data[selected_rows[0]]["lesson_number"])
    df = _get_filtered(*filter_values)
    row = df[df["lesson_number"] == lesson_number]
    if row.empty:
        return dbc.Alert("Lesson not found in filtered set.", color="warning")
    r = row.iloc[0]

    sections = [
        html.H4(r.get("title", "Untitled")),
        html.P([
            html.Strong("Lesson #"), r["lesson_number"], " · ",
            html.Strong("Date "), str(r.get("lesson_date", ""))[:10], " · ",
            html.Strong("Center "), r.get("organization", ""),
        ]),
        html.A("View on LLIS →", href=r.get("url", "#"), target="_blank"),
    ]

    if HAS_CLASSIFICATION:
        sections.append(html.Hr())
        sections.append(html.P([
            html.Strong("Primary agent: "),
            AGENT_LABELS.get(r.get("primary_agent"), r.get("primary_agent")),
        ]))
        if r.get("secondary_agents"):
            labels = [AGENT_LABELS.get(a, a) for a in r["secondary_agents"]]
            sections.append(html.P([html.Strong("Secondary agents: "), ", ".join(labels)]))
        if r.get("failure_patterns"):
            labels = [PATTERN_LABELS.get(p, p) for p in r["failure_patterns"]]
            sections.append(html.P([html.Strong("Failure patterns: "), ", ".join(labels)]))
        sections.append(html.P([
            html.Strong("Impact: "), r.get("impact_severity", "unknown"),
            " — ", r.get("impact_notes") or "",
        ]))
        if r.get("evidence"):
            sections.append(html.H5("Evidence"))
            sections.extend([
                html.Blockquote(f"“{e.get('quote', '')}” ({e.get('field', '')})")
                for e in r["evidence"]
            ])

    for label, field in [
        ("Abstract", "abstract_text"),
        ("Driving event", "driving_event_text"),
        ("Lesson", "lesson_text"),
        ("Recommendation", "recommendation_text"),
    ]:
        text = r.get(field)
        if text:
            sections.extend([html.H5(label), html.P(text)])

    return dbc.Card(dbc.CardBody(sections))


@app.callback(
    Output("download-export", "data"),
    Input("export-btn", "n_clicks"),
    *FILTER_INPUTS,
    prevent_initial_call=True,
)
def export_csv(_n, *filter_values):
    df = _get_filtered(*filter_values)
    return dcc.send_data_frame(explode_for_export(df).to_csv, "llis_filtered.csv", index=False)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
