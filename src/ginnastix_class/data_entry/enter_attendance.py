import os
import pickle
from datetime import date
from datetime import datetime
from datetime import timedelta
from functools import cached_property
from functools import reduce
from pathlib import Path

import pandas as pd

from ginnastix_class.utils.google_sheets import append_dataset_rows
from ginnastix_class.utils.google_sheets import authenticate
from ginnastix_class.utils.google_sheets import read_dataset
from ginnastix_class.utils.user_input import get_input
from ginnastix_class.utils.user_input import get_input_from_df


class Attendance:
    _credentials = None
    _data_dir = "data"
    _expected_attendance_rate = 0.8
    Path(_data_dir).mkdir(parents=True, exist_ok=True)

    def __init__(self, reference_dataset_source, resume_data_entry=False):
        self._source = reference_dataset_source
        self._resume_data_entry = resume_data_entry
        self.df_class_sessions = self.read_reference_dataset("class_sessions")
        self.df_student_classes = self.read_reference_dataset("student_classes")
        self.df_holidays = self.read_reference_dataset("holidays")

        # Set when self.initialize_class_session() is called
        self.date_str = None
        self.day = None
        self.dt = None
        self.students = None

    @property
    def credentials(self):
        if not self._credentials or not self._credentials.valid:
            self._credentials = authenticate()
        return self._credentials

    @property
    def bool_options(self):
        return {0: "no", 1: "yes"}

    @cached_property
    def out_file(self):
        return os.path.join(self._data_dir, "output.csv")

    @cached_property
    def class_days(self):
        # TODO: clean up
        self.df_student_classes["Start"] = self.df_student_classes["Start"].apply(
            self.norm_date_string
        )
        self.df_holidays["DT"] = self.df_holidays["Date"].apply(self.to_dt)

        min_timestamp = self.df_student_classes["Start"].apply(self.to_dt).min()
        all_dates = []
        _date = min_timestamp
        while _date <= datetime.now():
            all_dates.append((_date, _date.strftime("%A")))
            _date += timedelta(days=1)
        df_dates = pd.DataFrame(all_dates, columns=["DT", "Day"])
        df = pd.merge(
            df_dates,
            self.df_class_sessions[["Day", "Class"]],
            on="Day",
            how="inner",
        )
        df2 = pd.merge(
            df,
            self.df_student_classes[["Student", "Class", "Start"]],
            on="Class",
            how="inner",
        )
        df3 = pd.merge(
            df2,
            self.df_holidays[["DT", "Holiday"]],
            on="DT",
            how="left",
        )
        df3 = df3[
            (df3["Holiday"].isna()) & (df3["Start"].apply(self.to_dt) <= df3["DT"])
        ][["DT", "Day", "Class", "Student"]]
        df3["Date"] = df3["DT"].apply(self.norm_date_string)

        return df3

    @cached_property
    def date_info(self):
        # TODO: clean up
        max_display = 6
        dates = []
        for _date, _ in self.class_days.groupby(["Date", "Day"]):
            dates.append(_date)
        dates = sorted(dates, key=lambda x: x[0], reverse=True)[0:max_display]
        dates.append(("OTHER", ""))
        date_str, day = get_input_from_df(
            df=pd.DataFrame(dates, columns=["Date", "Day"]),
            attr="Date",
            attr_desc="Day",
            prompt="Enter your date",
        )
        if date_str != "OTHER":
            dt = datetime.strptime(date_str, "%m/%d/%Y")
        else:
            while True:
                _input = get_input("What date?")
                try:
                    dt = datetime.strptime(_input, "%m/%d/%Y")
                    date_str = dt.strftime("%m/%d/%Y")
                    day = dt.strftime("%A")
                    if self.class_days[
                        (self.class_days["Date"] == date_str)
                        & (self.class_days["Day"] == day)
                    ].empty:
                        print(f"Class is not held on {_input}. Enter a different date.")
                    else:
                        break
                except Exception as e:
                    print(f"Invalid input: {e}. Enter a different date.")
        return dt, date_str, day

    def to_dt(self, x):
        if x:
            return datetime.strptime(x, "%m/%d/%Y")
        else:
            return pd.NaT

    def norm_date_string(self, x):
        if isinstance(x, str):
            res = datetime.strptime(x, "%m/%d/%Y").strftime("%m/%d/%Y")
        elif isinstance(x, datetime) or isinstance(x, date):
            res = x.strftime("%m/%d/%Y")
        else:
            res = x
        return res

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

    @cached_property
    def attendance_attributes(self):
        return [
            "Attended Class",
            "On Time",
            "Prepared",
            "Kind To Others",
            "Listened To Instructions",
            "Completed Assignments",
            "Focused Mindset",
            "Positive Attitude",
            "Pain Free",
        ]

    def read_raw_df(self):
        return pd.read_csv(
            self.out_file,
            header=None,
            names=[
                "Athlete",
                "Date",
                "Day",
                *self.attendance_attributes,
                "Notes",
            ],
            na_values=[val for val in pd._libs.parsers.STR_NA_VALUES if val != "n/a"],
            keep_default_na=False,
            sep=",",
        )

    def initialize_class_session(self):
        dt, date_str, day = self.date_info
        processed_students = []
        if self._resume_data_entry and os.path.exists(self.out_file):
            df_partial_batch = self.read_raw_df()
            date_str = df_partial_batch["Date"].values[0]
            day = df_partial_batch["Day"].values[0]
            dt = self.to_dt(date_str)
            processed_students = df_partial_batch["Athlete"].to_list()

        self.df_student_classes["Is Active"] = self.df_student_classes["Stop"].apply(
            lambda x: not (self.to_dt(x) < dt)
        )
        self.class_days = pd.merge(
            self.class_days,
            self.df_student_classes[["Student", "Class", "Is Active"]],
            on=["Student", "Class"],
            how="left",
        )
        all_students = sorted(
            self.class_days[
                (self.class_days["DT"] == dt) & (self.class_days["Is Active"])
            ]["Student"].to_list()
        )
        students = sorted(list(set(all_students) - set(processed_students)))

        # Store class attributes
        self.date_str = date_str
        self.day = day
        self.dt = dt
        self.students = students

    def collect_attendance(self):
        print(f"Entering attendance information for {self.day} {self.date_str} ...")
        absent_students = get_input(
            "Any absent students?", options=self.students, multi=True
        )
        present_students = sorted(list(set(self.students).difference(absent_students)))
        late_students = get_input(
            "Any late students?", options=present_students, multi=True
        )
        unprepared_students = get_input(
            "Any unprepared students?", options=present_students, multi=True
        )
        injured_students = get_input(
            "Any injured students?", options=present_students, multi=True
        )
        problem_students = get_input(
            "Any students with behavioral issues?", options=present_students, multi=True
        )

        print("Entering athlete-specific information ...")
        options = ["No", "Somewhat", "Mostly", "Yes"]
        for _student in self.students:
            # Set defaults
            _ac = _ot = _p = _kto = _lti = _ca = _fm = _pa = _pf = "Yes"
            _notes = ""

            print(f"\n------------ {_student} ------------\n")
            if _student in absent_students:
                _ac = "No"
                _ot = _p = _kto = _lti = _ca = _fm = _pa = _pf = ""
            if _student in late_students:
                _ot = "No"
            if _student in unprepared_students:
                _p = "No"
            if _student in injured_students:
                _pf = "No"
            if _student in problem_students:
                _kto = get_input("[Kind To Others]", options=options)
                _lti = get_input("[Listened To Instructions]", options=options)
                _ca = get_input("[Completed Assignments]", options=options)
                _fm = get_input("[Focused Mindset]", options=options)
                _pa = get_input("[Positive Attitude]", options=options)

            values = [_ac, _ot, _p, _kto, _lti, _ca, _fm, _pa, _pf]
            summary = [
                f"{attr} - {value}"
                for attr, value in zip(self.attendance_attributes, values)
                if value not in ("Yes", "")
            ]
            divider = "\n----------------------------\n"
            summary_text = "\n".join(summary) or "(perfect behavior)"
            _notes = get_input(
                f"Any additional notes about {_student}?"
                f"{divider}{summary_text}{divider}"
            )

            # Incrementally store row
            row = [_student, self.date_str, self.day] + values + [_notes]
            columns = [
                "Athlete",
                "Date",
                "Day",
                *self.attendance_attributes,
                "Notes",
            ]
            df_out = pd.DataFrame([row], columns=columns)
            df_out.to_csv(
                self.out_file, mode="a", header=False, columns=None, index=False
            )

    def process_batch(self):
        df_batch = self.read_raw_df()
        for col in self.attendance_attributes:
            df_batch[f"{col} Score"] = df_batch[col].map(
                {
                    "Yes": 1,
                    "Mostly": 2 / 3,
                    "Somewhat": 1 / 3,
                    "No": 0,
                },
                na_action="ignore",
            )
        df_batch["Overall Behavior Score"] = df_batch[
            [
                f"{col} Score"
                for col in self.attendance_attributes
                if col not in ["Attended Class", "Pain Free"]
            ]
        ].mean(axis=1)
        df_batch["Expected Class Size"] = len(self.students)
        df_batch["Expected Attendance Rate"] = self._expected_attendance_rate
        df_batch["Inserted At"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return df_batch

    def add(self):
        self.initialize_class_session()
        self.collect_attendance()
        df_batch = self.process_batch()
        append_dataset_rows(dataset_name="attendance", df=df_batch)

        # Clean up staging file
        if os.path.exists(self.out_file):
            os.remove(self.out_file)

    def get_options_df(self, df, attr, attr_desc=None, select_values=None):
        _df = df.copy()

        conditions = [~_df[attr].isnull()]  # TODO: revisit null handling
        if select_values:
            conditions.extend([_df[col] == val for col, val in select_values.items()])
        select_condition = reduce(lambda c1, c2: c1 & c2, conditions[1:], conditions[0])

        _cols = [attr, attr_desc] if attr_desc else [attr]
        _df = _df[select_condition][_cols].drop_duplicates().reset_index(drop=True)

        if attr_desc:
            _df["options"] = _df[attr] + " - " + _df[attr_desc]
        else:
            _df["options"] = _df[attr]

        return _df
