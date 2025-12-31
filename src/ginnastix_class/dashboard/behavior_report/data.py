import json
import os
import pickle
from datetime import datetime

from ginnastix_class.dashboard.color import map_color
from ginnastix_class.utils.google_sheets import authenticate
from ginnastix_class.utils.google_sheets import read_dataset


class DataReader:
    _credentials = None
    _data_dir = "data"

    def __init__(self, dataset_source):
        self._source = dataset_source
        self.df_attendance = self.read_reference_dataset("attendance")
        self._validate(self.df_attendance)

        # Augment dataframe for reporting
        self.df_attendance["Dt"] = self.df_attendance["Date"].apply(
            lambda x: datetime.strptime(x, "%m/%d/%Y")
        )
        self.df_attendance["Overall Behavior Score (%)"] = (
            self.df_attendance["Overall Behavior Score"] * 100
        )
        self.df_attendance["Overall Behavior Score Color"] = map_color(
            self.df_attendance["Overall Behavior Score"]
        )

    @property
    def credentials(self):
        if not self._credentials or not self._credentials.valid:
            self._credentials = authenticate()
        return self._credentials

    @property
    def behavior_columns(self):
        return [
            "Attended Class Score",
            "On Time Score",
            "Prepared Score",
            "Kind To Others Score",
            "Listened To Instructions Score",
            "Completed Assignments Score",
            "Focused Mindset Score",
            "Positive Attitude Score",
            "Overall Behavior Score",
        ]

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

    def _validate(self, df):
        errors = []
        for col_name in self.behavior_columns:
            min_val = df[col_name].min()
            max_val = df[col_name].max()
            if min_val < 0:
                errors.append(f"Minimum value in column '{col_name}' is less than 0")
            if max_val > 1:
                errors.append(f"Maximum value in column '{col_name}' is greater than 1")
        if errors:
            raise ValueError(json.dumps(errors, indent=2))
