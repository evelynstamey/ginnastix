from datetime import datetime

import plotly.graph_objects as go
from dash import html

from ginnastix_class.dashboard.color import NEGATIVE_ACCENT
from ginnastix_class.dashboard.color import POSITIVE_ACCENT
from ginnastix_class.dashboard.color import rgb_arr


def get_headline_stats_summary_grid(df, athlete_name, min_datetime, max_datetime):
    min_datetime = min_datetime or datetime.min
    max_datetime = max_datetime or datetime.max
    dff = df[
        (df["Athlete"] == athlete_name)
        & (df["Dt"] >= min_datetime)
        & (df["Dt"] <= max_datetime)
    ]
    if dff.empty:
        return []

    divs = []
    headline_behavior_columns = [
        "Overall Behavior Score",
        "Attended Class Score",
    ]
    for _, col in enumerate(headline_behavior_columns):
        stat, color = get_behavior_stats(dff, col)
        _div = html.Div(
            className="headline-stats-summary-cell",
            children=[
                html.Div(
                    stat,
                    className="headline-stats-box",
                    style={"backgroundColor": color},
                ),
                html.Div(
                    col[:-6],
                    className="headline-description-box",
                ),
            ],
        )
        divs.append(_div)

    return divs


def get_stats_summary_grid(df, athlete_name, min_datetime, max_datetime):
    min_datetime = min_datetime or datetime.min
    max_datetime = max_datetime or datetime.max
    dff = df[
        (df["Athlete"] == athlete_name)
        & (df["Dt"] >= min_datetime)
        & (df["Dt"] <= max_datetime)
    ]
    if dff.empty:
        return []

    divs = []
    behavior_columns = [
        "On Time Score",
        "Prepared Score",
        "Kind To Others Score",
        "Listened To Instructions Score",
        "Completed Assignments Score",
        "Focused Mindset Score",
        "Positive Attitude Score",
    ]
    for _, col in enumerate(behavior_columns):
        stat, color = get_behavior_stats(dff, col)
        _div = html.Div(
            className="stats-summary-cell",
            children=[
                html.Div(
                    stat,
                    className="stats-box",
                    style={"backgroundColor": color},
                ),
                html.Div(
                    col[:-6],
                    className="description-box",
                ),
            ],
        )
        divs.append(_div)
    return divs


def get_behavior_stats(df, column_name):
    rgb = rgb_arr(101)
    student_mean = df[column_name].mean() * 100
    return f"{student_mean:.0f}%", rgb[int(student_mean)]


def get_overall_behavior_graph(
    df, athlete_name, min_datetime=None, max_datetime=None, expected_threshold=90
):
    # Filter and sort
    min_datetime = min_datetime or datetime.min
    max_datetime = max_datetime or datetime.max
    dff = df[
        (df["Athlete"] == athlete_name)
        & (df["Dt"] >= min_datetime)
        & (df["Dt"] <= max_datetime)
    ]
    dff = dff.sort_values(by="Dt").reset_index(drop=True)

    # Return early if no data
    if dff.empty:
        fig = go.Figure()
        fig.update_layout(
            xaxis={"visible": False},
            yaxis={"visible": False},
            annotations=[
                {
                    "text": f"No data available for {athlete_name}",
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {"size": 18},
                }
            ],
        )
        return fig

    # Calculate point statistics
    student_mean = dff["Overall Behavior Score (%)"].mean()
    # min_date = dff["Dt"].min().strftime("%m/%d/%Y")
    # max_date = dff["Dt"].max().strftime("%m/%d/%Y")

    # Figure specification
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=dff["Date"],
            y=dff["Overall Behavior Score (%)"],
            marker={"color": dff["Overall Behavior Score Color"]},
            showlegend=False,
        )
    )
    fig.add_shape(
        type="line",
        xref="paper",
        yref="y",
        x0=0,
        y0=expected_threshold,
        x1=1,
        y1=expected_threshold,
        line=dict(
            color="black",
            width=2,
            dash="dot",
        ),
        name=f"Class Expectation ({expected_threshold:.0f}%)",
        showlegend=True,
    )

    fig.add_shape(
        type="line",
        xref="paper",
        yref="y",
        x0=0,
        y0=student_mean,
        x1=1,
        y1=student_mean,
        line=dict(
            color=NEGATIVE_ACCENT
            if student_mean < expected_threshold
            else POSITIVE_ACCENT,
            width=2,
            dash="dot",
        ),
        name=f"{athlete_name.split(' ')[0]} Average ({student_mean:.0f}%)",
        showlegend=True,
    )

    fig.update_layout(
        title=dict(
            text="Class Behavior Summary",
            # subtitle={"text": f"({min_date} to {max_date})"},
            y=0.85,
            x=0,
            xanchor="left",
            yanchor="top",
        ),
        font=dict(color="black"),
        margin=dict(l=0, r=0),
        xaxis_title="Class Day",
        xaxis=dict(tickson="boundaries", ticklen=20),
        yaxis_range=[-5, 105],
        yaxis={"showgrid": False, "showticklabels": True},
        bargap=0,
        bargroupgap=0,
    )
    return fig
