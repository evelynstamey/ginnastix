import os

from dash import Dash
from dash import Input
from dash import Output
from dash import callback
from dash import dcc
from dash import html

from ginnastix_class.dashboard.behavior_report.components import (
    get_headline_stats_summary_grid,
)
from ginnastix_class.dashboard.behavior_report.components import (
    get_overall_behavior_graph,
)
from ginnastix_class.dashboard.behavior_report.components import get_stats_summary_grid
from ginnastix_class.dashboard.behavior_report.data import DataReader
from ginnastix_class.dashboard.behavior_report.data import get_date_list

"""
REF
    - https://plotly.com/python/plotly-express/
    - https://plotly.com/python/line-charts/
"""


def main(dataset_source="local", debug=False):
    global DF
    global DATE_LIST

    dr = DataReader(dataset_source)
    DF = dr.df_attendance
    DATE_LIST = get_date_list()
    dashboard_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"Dashboard path: {dashboard_dir}")
    app = Dash(
        __name__,
        assets_folder=os.path.join(dashboard_dir, "assets"),
        prevent_initial_callbacks="initial_duplicate",
    )
    app.layout = [
        html.Div(
            [
                # Dashboard title
                html.Div(
                    [
                        html.H1(children="Behavior Report"),
                    ],
                    className="container-flex-item",
                ),
                # Name filter options
                html.Div(
                    [
                        dcc.Dropdown(
                            sorted(DF["Athlete"].unique()),
                            placeholder="Select a student",
                            clearable=True,
                            id="athlete-name-dropdown",
                            className="athlete-name-dropdown",
                        ),
                    ],
                    className="container-flex-item",
                ),
            ],
            className="container-flex",
        ),
        # Date filter options
        dcc.RangeSlider(
            min=0,
            max=len(DATE_LIST) - 1,
            step=1,
            value=[len(DATE_LIST) - 7, len(DATE_LIST) - 1],
            marks={
                i: {"label": v, "style": {"white-space": "nowrap"}}
                for i, v in enumerate([i.strftime("%b-%y") for i in DATE_LIST])
            },
            allowCross=False,
            id="date-range-slider",
            className="date-range-slider",
        ),
        # Dashboard section #1
        html.Div(
            id="headline-stats-summary-grid",
            className="headline-stats-summary-grid",
        ),
        # Dashboard section #2
        html.Div(
            id="stats-summary-grid",
            className="stats-summary-grid",
        ),
        # Dashboard section #3
        html.Div(id="overall-behavior-graph", className="overall-behavior-graph"),
    ]
    app.run(debug=debug)


@callback(
    Output("stats-summary-grid", "children"),
    [Input("athlete-name-dropdown", "value"), Input("date-range-slider", "value")],
)
def stats_summary_grid(athlete_name, date_range):
    min_datetime = DATE_LIST[date_range[0]]
    max_datetime = DATE_LIST[date_range[1]]
    divs = get_stats_summary_grid(DF, athlete_name, min_datetime, max_datetime)
    return divs


@callback(
    Output("headline-stats-summary-grid", "children"),
    [Input("athlete-name-dropdown", "value"), Input("date-range-slider", "value")],
)
def headline_stats_summary_grid(athlete_name, date_range):
    min_datetime = DATE_LIST[date_range[0]]
    max_datetime = DATE_LIST[date_range[1]]
    divs = get_headline_stats_summary_grid(DF, athlete_name, min_datetime, max_datetime)
    return divs


@callback(
    Output("overall-behavior-graph", "children"),
    [Input("athlete-name-dropdown", "value"), Input("date-range-slider", "value")],
)
def overall_behavior_graph(athlete_name, date_range):
    min_datetime = DATE_LIST[date_range[0]]
    max_datetime = DATE_LIST[date_range[1]]
    if athlete_name is not None:
        fig = get_overall_behavior_graph(DF, athlete_name, min_datetime, max_datetime)
        return dcc.Graph(figure=fig)


if __name__ == "__main__":
    main()
