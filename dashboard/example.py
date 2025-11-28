import os
import pickle
import sys

import numpy as np
import plotly.graph_objects as go
from dash import Dash
from dash import Input
from dash import Output
from dash import callback
from dash import dcc
from dash import html

from utils.google_sheets import authenticate
from utils.google_sheets import read_dataset

"""
REF
    - https://plotly.com/python/plotly-express/
    - https://plotly.com/python/line-charts/
"""


class DataReader:
    _credentials = None
    _data_dir = "data"

    def __init__(self, dataset_source):
        self._source = dataset_source
        self.df_attendance = self.read_reference_dataset("attendance")

        # Process `df_attendance`
        self.df_attendance["Behavior Score (%)"] = self.df_attendance[
            "Overall Behavior Score"
        ].apply(lambda x: np.round(x, 2) * 100)

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


@callback(Output("graph-content", "figure"), Input("dropdown-selection", "value"))
def update_graph(value):
    dff = DF[DF["Athlete"] == value]
    student_mean = dff["Behavior Score (%)"].mean()

    # Create two traces: one for values above/at the threshold, one for values below
    fig = go.Figure()

    # Trace for values above or at the threshold
    fig.add_trace(
        go.Scatter(
            x=dff["Date"],
            y=dff["Behavior Score (%)"].where(dff["Behavior Score (%)"] >= THRESHOLD),
            mode="markers",
            marker=dict(color="blue", size=10),
            name=f"Above {THRESHOLD} %",
        )
    )
    # Trace for values below the threshold
    fig.add_trace(
        go.Scatter(
            x=dff["Date"],
            y=dff["Behavior Score (%)"].where(dff["Behavior Score (%)"] < THRESHOLD),
            mode="markers",
            marker=dict(color="red", size=10),
            name=f"Below {THRESHOLD} %",
        )
    )
    # Threshold
    fig.add_trace(
        go.Scatter(
            x=dff["Date"],
            y=[THRESHOLD] * dff.shape[0],
            mode="lines",
            # marker=dict(color="red", size=10),
            line=dict(color="grey", width=2, dash="dash"),
            name="Class expectation",
        )
    )
    # Threshold
    fig.add_trace(
        go.Scatter(
            x=dff["Date"],
            y=[student_mean] * dff.shape[0],
            mode="lines",
            # marker=dict(color="red", size=10),
            line=dict(
                color="blue" if student_mean >= THRESHOLD else "red",
                width=2,
                dash="dash",
            ),
            name="Student Average",
        )
    )

    fig.update_layout(
        title=None,
        xaxis_title="Class Date",
        yaxis_title="Behavior Score (%)",
    )
    return fig


if __name__ == "__main__":
    global DF
    global THRESHOLD

    dataset_source = "local"
    try:
        if "--clear-cache" in sys.argv:
            dataset_source = "gsheets"
    except Exception:
        pass

    dr = DataReader(dataset_source)
    DF = dr.df_attendance
    THRESHOLD = 90

    app = Dash()
    app.layout = [
        html.H1(children="Student Overall Behavior", style={"textAlign": "center"}),
        dcc.Dropdown(DF["Athlete"].unique(), "--", id="dropdown-selection"),
        dcc.Graph(id="graph-content"),
    ]

    app.run()
