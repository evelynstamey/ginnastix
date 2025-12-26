import plotly.graph_objects as go
from dash import html

from ginnastix_class.dashboard.color import rgb_arr


def get_stats_summary_grid(df, value, attrs):
    dff = df[df["Athlete"] == value]
    if dff.empty:
        return []

    divs = []
    for _, c in enumerate(attrs):
        stat, color = update_stats_box(dff, f"{c} Score")
        desc = update_description_box(f"{c} Score")
        _div = html.Div(
            className="stats-summary-cell",
            children=[
                html.Div(
                    stat,
                    className="stats-box",
                    style={"backgroundColor": color},
                ),
                html.Div(
                    desc,
                    className="description-box",
                ),
            ],
        )
        divs.append(_div)
    return divs


def update_stats_box(df, column_name):
    rgb = rgb_arr(101)
    student_mean = df[column_name].mean() * 100
    return f"{student_mean:.0f}%", rgb[int(student_mean)]


def update_description_box(column_name):
    return column_name[:-6]


def get_overall_behavior_graph(df, value, expected_threshold=90):
    # Filter and sort
    dff = df[df["Athlete"] == value]
    dff = dff.sort_values(by="Dt").reset_index(drop=True)

    # Return early if no data
    if dff.empty:
        fig = go.Figure()
        fig.update_layout(
            xaxis={"visible": False},
            yaxis={"visible": False},
            annotations=[
                {
                    "text": f"No data available for {value}",
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
    min_date = dff["Dt"].min().strftime("%m/%d/%Y")
    max_date = dff["Dt"].max().strftime("%m/%d/%Y")

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
    if student_mean < expected_threshold:
        fig.add_trace(
            go.Scatter(
                x=dff["Date"],
                y=[student_mean] * dff.shape[0],
                mode="lines",
                line=dict(
                    color="#f04f0a",
                    width=2,
                ),
                name=f"Average Score ({student_mean:.2f}%)",
            )
        )
    fig.update_layout(
        height=400,
        title={
            "text": "Class Behavior",
            "subtitle": {"text": f"({min_date} to {max_date})"},
        },
        xaxis_title="Class Day",
        yaxis_title="Score (%)",
        xaxis={"showgrid": False, "showticklabels": False},
        yaxis_range=[-5, 105],
        yaxis={"showgrid": False, "showticklabels": True},
        bargap=0,
        bargroupgap=0,
    )
    return fig
