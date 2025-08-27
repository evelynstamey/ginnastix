import os
import pickle
from datetime import date
from datetime import datetime
from datetime import timedelta
from functools import cached_property
from functools import reduce

import pandas as pd

from utils.google_sheets import append_dataset_rows
from utils.google_sheets import authenticate
from utils.google_sheets import read_dataset


class Attendance:
    _credentials = None
    _data_dir = "data"
    _expected_attendance_rate = 0.8

    def __init__(self, reference_dataset_source, resume_data_entry=False):
        self._source = reference_dataset_source
        self._resume_data_entry = resume_data_entry
        self.df_class_sessions = self.read_reference_dataset("class_sessions")
        self.df_student_classes = self.read_reference_dataset("student_classes")
        self.df_holidays = self.read_reference_dataset("holidays")

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
        df_active_student_classes = self.df_student_classes[
            self.df_student_classes["Stop"].isna()
        ]
        current_timestamp = datetime.now()
        min_timestamp = df_active_student_classes["Start"].apply(self.to_dt).min()
        all_dates = []
        _date = min_timestamp
        while _date <= current_timestamp:
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
            df_active_student_classes[["Student", "Class", "Start"]],
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
        date, day = self.get_input_from_df(
            df=pd.DataFrame(dates, columns=["Date", "Day"]),
            attr="Date",
            attr_desc="Day",
            prompt="Enter your date",
        )
        if date != "OTHER":
            dt = datetime.strptime(date, "%m/%d/%Y")
        else:
            while True:
                _input = self.get_input("What date?")
                try:
                    dt = datetime.strptime(_input, "%m/%d/%Y")
                    date = dt.strftime("%m/%d/%Y")
                    day = dt.strftime("%A")
                    if self.class_days[
                        (self.class_days["Date"] == date)
                        & (self.class_days["Day"] == day)
                    ].empty:
                        print(f"Class is not held on {_input}. Enter a different date.")
                    else:
                        break
                except Exception as e:
                    print(f"Invalid input: {e}. Enter a different date.")
        return dt, date, day

    def to_dt(self, x):
        return datetime.strptime(x, "%m/%d/%Y")

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

    def add(self):
        # # TODO: clean up
        attr_cols = [
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
        if self._resume_data_entry:
            df_partial_batch = pd.read_csv(
                self.out_file,
                header=None,
                names=[
                    "Athlete",
                    "Date",
                    "Day",
                    *attr_cols,
                    "Notes",
                ],
                na_values=[
                    val for val in pd._libs.parsers.STR_NA_VALUES if val != "n/a"
                ],
                keep_default_na=False,
                sep=",",
            )
            _date = df_partial_batch["Date"].values[0]
            _day = df_partial_batch["Day"].values[0]
            _dt = self.to_dt(_date)
            _processed_students = df_partial_batch["Athlete"].to_list()
            _all_students = sorted(
                self.class_days[self.class_days["DT"] == _dt]["Student"].to_list()
            )
            _students = sorted(list(set(_all_students) - set(_processed_students)))
        else:
            _dt, _date, _day = self.date_info
            _students = sorted(
                self.class_days[self.class_days["DT"] == _dt]["Student"].to_list()
            )

        print(f"Entering attendance information for {_day} {_date} ...")
        absent_students = self.get_input(
            "Any absent students?", options=_students, multi=True
        )
        present_students = sorted(list(set(_students).difference(absent_students)))
        late_students = self.get_input(
            "Any late students?", options=present_students, multi=True
        )
        unprepared_students = self.get_input(
            "Any unprepared students?", options=present_students, multi=True
        )
        injured_students = self.get_input(
            "Any injured students?", options=present_students, multi=True
        )
        problem_students = self.get_input(
            "Any students with behavioral issues?", options=present_students, multi=True
        )

        print("Entering athlete-specific information ...")
        options = ["No", "Somewhat", "Mostly", "Yes"]
        for _student in _students:
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
                _kto = self.get_input("[Kind To Others]", options=options)
                _lti = self.get_input("[Listened To Instructions]", options=options)
                _ca = self.get_input("[Completed Assignments]", options=options)
                _fm = self.get_input("[Focused Mindset]", options=options)
                _pa = self.get_input("[Positive Attitude]", options=options)

            values = [_ac, _ot, _p, _kto, _lti, _ca, _fm, _pa, _pf]
            summary = [
                f"{attr} - {value}"
                for attr, value in zip(attr_cols, values)
                if value not in ("Yes", "")
            ]
            divider = "\n----------------------------\n"
            summary_text = "\n".join(summary)
            _notes = self.get_input(
                f"Any additional notes about {_student}?"
                f"{divider}{summary_text}{divider}"
            )

            # Incrementally store row
            row = [_student, _date, _day] + values + [_notes]
            columns = [
                "Athlete",
                "Date",
                "Day",
                *attr_cols,
                "Notes",
            ]
            df_out = pd.DataFrame([row], columns=columns)
            df_out.to_csv(
                self.out_file, mode="a", header=False, columns=None, index=False
            )

        df_batch = pd.read_csv(
            self.out_file,
            header=None,
            names=[
                "Athlete",
                "Date",
                "Day",
                *attr_cols,
                "Notes",
            ],
            na_values=[val for val in pd._libs.parsers.STR_NA_VALUES if val != "n/a"],
            keep_default_na=False,
            sep=",",
        )
        for col in attr_cols:
            df_batch[f"{col} (Score)"] = df_batch[col].map(
                {
                    "Yes": 1,
                    "Mostly": 2 / 3,
                    "Somewhat": 1 / 3,
                    "No": 0,
                },
                na_action="ignore",
            )
        df_batch["Expected Class Size"] = len(_students)
        df_batch["Expected Attendance Rate"] = self._expected_attendance_rate
        df_batch["Inserted At"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        append_dataset_rows(dataset_name="attendance", df=df_batch)

        # Clean up staging file
        if os.path.exists(self.out_file):
            os.remove(self.out_file)

    def get_options_df(self, df, attr, attr_desc=None, select_values=None):
        _df = df.copy()

        conditions = [_df[attr] != ""]
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

    def get_input_from_df(self, prompt, df, attr, attr_desc=None, select_values=None):
        df_options = self.get_options_df(df, attr, attr_desc, select_values)
        options = df_options["options"].to_dict()
        value = ""
        value_desc = ""
        if options:
            _input = self.get_input(prompt, options)
            df_selected_option = df_options[df_options["options"] == _input]
            value = df_selected_option[attr].values[0]
            if attr_desc:
                value_desc = df_selected_option[attr_desc].values[0]
        return value, value_desc

    def get_input(self, prompt, options=None, multi=False):
        while True:
            try:
                return self._get_input(prompt, options, multi)
            except Exception as e:
                print(f"Invalid input ({e})")

    def _get_input(self, prompt, options=None, multi=False):
        if not options:
            return input(f"\n{prompt}\n\n>>> ")

        if isinstance(options, dict):
            options_text = "\n".join(
                f"  [{idx + 1}]: {val}" for idx, val in options.items()
            )
        else:
            options_text = "\n".join(
                f"  [{idx + 1}]: {val}" for idx, val in enumerate(options)
            )

        x = input(f"\n{prompt}\n{options_text}\n\n>>> ")
        if multi:
            if x:
                return [options[int(i) - 1] for i in x.split(",")]
            else:
                return []
        else:
            return options[int(x) - 1]
