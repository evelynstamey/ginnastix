import json
import os
import pickle
from datetime import datetime
from functools import cached_property
from functools import reduce

import pandas as pd

from utils.google_sheets import append_dataset_rows
from utils.google_sheets import authenticate
from utils.google_sheets import read_dataset


class SkillEvaluation:
    _credentials = None
    _data_dir = "data"

    def __init__(self, reference_dataset_source):
        self._source = reference_dataset_source

        self.df_periods = self.read_reference_dataset("periods")
        self.df_levels = self.read_reference_dataset("levels")
        self.df_events = self.read_reference_dataset("events")
        self.df_skills = self.read_reference_dataset("skills")
        self.df_student_classes = self.read_reference_dataset("student_classes")
        self.df_student_levels = self.read_reference_dataset("student_levels")

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
    def evaluation_period(self):
        options = self.df_periods["Period"].to_dict()
        return self.get_input("Enter your evaluation period", options)

    @cached_property
    def students(self):
        # Get initial list of students
        level, level_desc = self.get_input_from_df(
            df=self.df_levels,
            attr="Level",
            attr_desc="Level Description",
            prompt="Enter your student level",
        )
        df_active_students = self.df_student_classes[
            self.df_student_classes["Stop"].isna()
        ]
        df_active_students = pd.merge(
            df_active_students, self.df_student_levels, on="Student", how="left"
        )[["Student", "Level"]]
        all_students = df_active_students["Student"].to_list()
        students = df_active_students[df_active_students["Level"] == level][
            "Student"
        ].to_list()
        students = sorted(list(set(students)))
        print(
            f"\nYou selected {len(students)} students from the {level_desc.title()} team: "
            f"{json.dumps(students)}"
        )

        # Optionally add students
        _input = self.get_input(
            "Would you like to add any other students?", self.bool_options
        )
        if _input == "yes":
            options = dict(enumerate([s for s in all_students if s not in students]))
            names = self.get_input(
                "Which students would you like to add?", options, multi=True
            )
            students.extend(names)
            students = sorted(list(set(students)))
            print(
                f"\nYou selected {len(students)} students from the {level_desc.title()} team: "
                f"{json.dumps(students)}"
            )

        # Optionally remove students
        _input = self.get_input(
            "Would you like to remove any students?", self.bool_options
        )
        if _input == "yes":
            options = dict(enumerate(students))
            names = self.get_input(
                "Which students would you like to remove?", options, multi=True
            )
            students = [x for x in students if x not in names]
            students = sorted(list(set(students)))
            print(
                f"\nYou selected {len(students)} students from the {level_desc.title()} team: "
                f"{json.dumps(students)}"
            )

        return students

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
        _evaluation_period = self.evaluation_period
        _students = self.students

        continue_data_entry = True
        while continue_data_entry:
            # event
            _event, _event_desc = self.get_input_from_df(
                df=self.df_events,
                attr="Event",
                attr_desc="Event Description",
                prompt="Enter your event",
            )

            # skill
            _event_skill, _event_skill_desc = self.get_input_from_df(
                df=self.df_skills,
                attr="Skill",
                attr_desc="Skill Description",
                select_values={"Event": _event},
                prompt=f"Enter your {_event_desc} skill",
            )

            # skill variant
            _event_skill_variant, _event_skill_variant_desc = self.get_input_from_df(
                df=self.df_skills,
                attr="Variant",
                attr_desc="Variant Description",
                select_values={"Event": _event, "Skill": _event_skill},
                prompt=f"Enter your skill variant for {_event_skill_desc}",
            )

            # get stats
            full_skill_description = (
                f"{_event_skill_desc} ({_event_skill_variant_desc})"
                if _event_skill_variant_desc
                else _event_skill_desc
            )
            print(f"Enter your skill scores for {full_skill_description}")
            for _student in _students:
                # Get score (if given)
                _score = input(f"{_student} >>> ")
                if _score not in ["0", "1", "2", "3", "4", "5"]:
                    print("Skipping student")
                    continue

                # Get dimensional attributes
                student_info = self.df_student_levels[
                    self.df_student_levels["Student"] == _student
                ]
                _level = student_info["Level"].values[0]
                skill_info = self.df_skills[
                    (self.df_skills["Skill"] == _event_skill)
                    & (self.df_skills["Variant"] == _event_skill_variant)
                ]
                _skill_id = skill_info["Skill ID"].values[0]
                _event_skill_id = skill_info["Event Skill ID"].values[0]
                _status = skill_info[_level].values[0]
                row = [
                    _evaluation_period,
                    _event,
                    _event_skill,
                    _event_skill_variant,
                    _student,
                    _score,
                    _skill_id,
                    _event_skill_id,
                    _level,
                    _status,
                ]

                # Incrementally store row
                with open(self.out_file, "a") as file:
                    file.write(",".join(row) + "\n")

            _input = self.get_input(
                "Would you like to add other skill?", self.bool_options
            )

            if _input == "no":  # Write batch and break out of loop
                df_batch = pd.read_csv(
                    self.out_file,
                    header=None,
                    names=[
                        "Period",
                        "Event",
                        "Skill",
                        "Variant",
                        "Athlete",
                        "Score",
                        "Skill ID",
                        "Event Skill ID",
                        "Level",
                        "Status",
                    ],
                    na_values=[
                        val for val in pd._libs.parsers.STR_NA_VALUES if val != "n/a"
                    ],
                    keep_default_na=False,
                )
                df_batch["Inserted At"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                append_dataset_rows(dataset_name="skill_evaluation", df=df_batch)
                continue_data_entry = False

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
        if not options:
            return input(f"\n{prompt}\n\n>>> ")
        options_text = "\n".join(
            f"  [{idx + 1}]: {val}" for idx, val in options.items()
        )
        x = input(f"\n{prompt}\n{options_text}\n\n>>> ")
        if multi:
            return [options[int(i) - 1] for i in x.split(",")]
        else:
            return options[int(x) - 1]
