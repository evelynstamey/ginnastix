import os
import pickle
from datetime import datetime

import matplotlib.colors as mcolors
import numpy as np
import plotly.graph_objects as go
from dash import Dash
from dash import Input
from dash import Output
from dash import callback
from dash import dcc
from dash import html

from ginnastix_class.utils.google_sheets import authenticate
from ginnastix_class.utils.google_sheets import read_dataset

"""
REF
    - https://plotly.com/python/plotly-express/
    - https://plotly.com/python/line-charts/
"""

BEHAVIOR_ATTRIBUTES = [
    "On Time",
    "Prepared",
    "Kind To Others",
    "Listened To Instructions",
    "Completed Assignments",
    "Focused Mindset",
    "Positive Attitude",
]
THRESHOLD = 90

samples = 101
cmap = mcolors.LinearSegmentedColormap.from_list(
    "custom_linear_cmap",
    ["#f04f0a"] * 10 + ["#e89e1e"] * 3 + ["#abb53f"] * 2 + ["#208c6f"],
    N=samples,
)
values = [cmap(i)[:3] for i in np.linspace(0, 1, samples)]
RGB = [f"rgb({int(r * 255)},{int(g * 255)},{int(b * 255)})" for r, g, b in values]


class DataReader:
    _credentials = None
    _data_dir = "data"

    def __init__(self, dataset_source):
        self._source = dataset_source
        self.df_attendance = self.read_reference_dataset("attendance")

        self.df_attendance["Dt"] = self.df_attendance["Date"].apply(
            lambda x: datetime.strptime(x, "%m/%d/%Y")
        )

    @property
    def credentials(self):
        if not self._credentials or not self._credentials.valid:
            self._credentials = authenticate()
        return self._credentials

    def read_reference_dataset(self, name):
        file_name = os.path.join(self._data_dir, f"{name}.pkl")
        if self._source == "local":
            print(f"Loading local dataset from file: {file_name}")
            try:
                with open(file_name, "rb") as f:
                    df = pickle.load(f)
                    return df
            except Exception as e:
                print(f"Failed to load local dataset from file: {e}")

        print(f"Reading dataset from Google Sheets: {name}")
        df = read_dataset(dataset_name=name, credentials=self.credentials)
        with open(file_name, "wb") as f:
            pickle.dump(df, f)

        return df


def main(dataset_source="local"):
    global DF

    dr = DataReader(dataset_source)
    DF = dr.df_attendance
    dashboard_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Dashboard path: {dashboard_dir}")
    app = Dash(
        __name__,
        assets_folder=os.path.join(dashboard_dir, "assets"),
        prevent_initial_callbacks="initial_duplicate",
    )
    app.layout = [
        html.H1(children="Behavior Report", style={"textAlign": "center"}),
        dcc.Dropdown(
            sorted(DF["Athlete"].unique()),
            "--",
            id="dropdown-selection",
            className="dropdown-selection",
        ),
        html.Div(
            id="stats-summary-grid",
            className="stats-summary-grid",
            children=[],
        ),
        html.Div(id="overall-behavior-graph"),
    ]
    app.run(debug=True)


def update_stats_box(df, column_name):
    student_mean = df[column_name].mean()
    stat = int(round(student_mean * 100, 0))
    return f"{stat}%", RGB[stat]


def update_description_box(column_name):
    return column_name[:-6]


@callback(
    Output("stats-summary-grid", "children"), Input("dropdown-selection", "value")
)
def stats_summary_grid(value):
    divs = []
    if not value:
        return divs
    dff = DF[DF["Athlete"] == value]
    for i, c in enumerate(BEHAVIOR_ATTRIBUTES):
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


@callback(
    Output("overall-behavior-graph", "children"), [Input("dropdown-selection", "value")]
)
def overall_behavior_graph(value):
    if value is None:
        return None
    else:
        fig = get_overall_behavior_graph(value)
        return dcc.Graph(figure=fig)


def get_color(x):
    if not x >= 0:
        return "#000000"
    if x >= THRESHOLD:
        return "#b3b3b3"
    if x < THRESHOLD:
        return "#ff9d73"


def get_overall_behavior_graph(value):
    if not value:
        return None
    dff = DF[DF["Athlete"] == value]
    dff = dff.sort_values(by="Dt").reset_index(drop=True)
    dff["Behavior Score (%)"] = dff["Overall Behavior Score"].apply(
        lambda x: np.round(x, 2) * 100
    )
    dff["bar_color"] = (
        dff["Behavior Score (%)"]
        .astype("Int64")
        .apply(lambda x: "rgb(0,0,0)" if not x >= 0 else RGB[int(x)])
    )
    dff["bar_color2"] = dff["Behavior Score (%)"].astype("Int64").apply(get_color)
    student_mean = dff["Overall Behavior Score"].mean()
    student_mean = int(round(student_mean * 100, 0))

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=dff["Date"],
            y=dff["Behavior Score (%)"],
            marker={"color": dff["bar_color"]},
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=dff["Date"],
            y=[THRESHOLD] * dff.shape[0],
            mode="lines",
            line=dict(color="black", width=1, dash="dot"),
            name="Class Expectation (90%)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=dff["Date"],
            y=[student_mean] * dff.shape[0],
            mode="lines",
            line=dict(
                color="black" if student_mean >= THRESHOLD else "#f04f0a",
                width=2,
            ),
            name=f"Average Score ({student_mean}%)",
        )
    )

    min_date = dff["Dt"].min().strftime("%m/%d/%Y")
    max_date = dff["Dt"].max().strftime("%m/%d/%Y")
    fig.update_layout(
        title={
            "text": "Class Behavior",
            "subtitle": {"text": f"({min_date} to {max_date})"},
        },
        xaxis_title="Class Day",
        yaxis_title="Score (%)",
        xaxis={"showgrid": False, "showticklabels": False},
        height=400,
        yaxis_range=[-5, 105],
        yaxis={"tickvals": [0, 20, 40, 60, 80, 100]},
        bargap=0,
        bargroupgap=0,
    )
    return fig


if __name__ == "__main__":
    main()
