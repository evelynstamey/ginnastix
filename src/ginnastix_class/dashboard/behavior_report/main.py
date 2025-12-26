import os

from dash import Dash
from dash import Input
from dash import Output
from dash import callback
from dash import dcc
from dash import html

from ginnastix_class.dashboard.behavior_report.components import (
    get_overall_behavior_graph,
)
from ginnastix_class.dashboard.behavior_report.components import get_stats_summary_grid
from ginnastix_class.dashboard.behavior_report.data import DataReader

"""
REF
    - https://plotly.com/python/plotly-express/
    - https://plotly.com/python/line-charts/
"""


def main(dataset_source="local", debug=False):
    global DF
    global BEHAVIOR_ATTRIBUTES

    dr = DataReader(dataset_source)
    DF = dr.df_attendance
    BEHAVIOR_ATTRIBUTES = dr.behavior_attributes
    dashboard_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
            placeholder="Select a student",
            clearable=True,
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
    app.run(debug=debug)


@callback(
    Output("stats-summary-grid", "children"), Input("dropdown-selection", "value")
)
def stats_summary_grid(value):
    divs = get_stats_summary_grid(DF, value, attrs=BEHAVIOR_ATTRIBUTES)
    return divs


@callback(
    Output("overall-behavior-graph", "children"), [Input("dropdown-selection", "value")]
)
def overall_behavior_graph(value):
    if value is not None:
        fig = get_overall_behavior_graph(DF, value)
        return dcc.Graph(figure=fig)


if __name__ == "__main__":
    main()
