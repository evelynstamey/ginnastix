import json
import os
import pickle
import sys
from functools import reduce

import pandas as pd

from utils.google_sheets import append_dataset_rows
from utils.google_sheets import authenticate
from utils.google_sheets import read_dataset


def read_reference_datasets(source):
    datasets = ["periods", "levels", "events", "skills", "student_levels"]
    creds = authenticate()
    dfs = []
    for name in datasets:
        _df = _read_reference_dataset(source, name, creds)
        dfs.append(_df)
    return tuple(dfs)


def _read_reference_dataset(source, name, creds):
    file_name = f"{name}.pkl"
    if source == "local":
        print(f"Loading local dataset from file: {file_name}")
        try:
            with open(file_name, "rb") as f:
                df = pickle.load(f)
                return df
        except Exception as e:
            print(f"Failed to load local dataset from file: {e}")

    print(f"Reading dataset from Google Sheets: {name}")
    df = read_dataset(dataset_name=name, credentials=creds)
    with open(file_name, "wb") as f:
        pickle.dump(df, f)
    return df


def process_user_inputs(df_periods, df_levels, df_events, df_skills, df_student_levels):
    # period
    options = df_periods["Period"].to_dict()
    options_text = "\n".join(f"  [{idx + 1}]: {val}" for idx, val in options.items())
    x = input(f"\nEnter your evaluation period:\n{options_text}\n\n>>> ")
    period = options[int(x) - 1]

    # students
    level, level_desc = process_user_input(
        df=df_levels,
        attr="Level",
        attr_desc="Level Description",
        prompt="Enter your student level",
    )
    students = sorted(
        df_student_levels[df_student_levels["Level"] == level]["Name"].to_list()
    )
    print(
        f"\nYou selected {len(students)} students from the {level_desc.title()} team: {json.dumps(students)}"
    )
    options = {0: "no", 1: "yes"}
    options_text = "\n".join(f"  [{idx + 1}]: {val}" for idx, val in options.items())
    x = input(f"\nWould you like to add any other students?\n{options_text}\n\n>>> ")
    if options[int(x) - 1] == "yes":
        options = (
            df_student_levels[~df_student_levels["Name"].isin(students)]["Name"]
            .reset_index(drop=True)
            .to_dict()
        )
        options_text = "\n".join(
            f"  [{idx + 1}]: {val}" for idx, val in options.items()
        )
        x = input(f"\nWhich students would you like to add?\n{options_text}\n\n>>> ")
        names = [options[int(i) - 1] for i in x.split(",")]
        students.extend(names)
        students = sorted(list(set(students)))
    print(
        f"\nYou selected {len(students)} students from the {level_desc.title()} team: {json.dumps(students)}"
    )
    options = {0: "no", 1: "yes"}
    options_text = "\n".join(f"  [{idx + 1}]: {val}" for idx, val in options.items())
    x = input(f"\nWould you like to remove any students?\n{options_text}\n\n>>> ")
    if options[int(x) - 1] == "yes":
        options = (
            df_student_levels[df_student_levels["Name"].isin(students)]["Name"]
            .reset_index(drop=True)
            .to_dict()
        )
        options_text = "\n".join(
            f"  [{idx + 1}]: {val}" for idx, val in options.items()
        )
        x = input(f"\nWhich students would you like to remove?\n{options_text}\n\n>>> ")
        names = [options[int(i) - 1] for i in x.split(",")]
        students = [x for x in students if x not in names]
        students = sorted(list(set(students)))
    print(
        f"\nYou selected {len(students)} students from the {level_desc.title()} team: {json.dumps(students)}"
    )

    continue_data_entry = True
    while continue_data_entry:
        # event
        event, event_desc = process_user_input(
            df=df_events,
            attr="Event",
            attr_desc="Event Description",
            prompt="Enter your event",
        )

        # skill
        event_skill, event_skill_desc = process_user_input(
            df=df_skills,
            attr="Skill",
            attr_desc="Skill Description",
            select_values={"Event": event},
            prompt=f"Enter your {event_desc} skill",
        )

        # skill variant
        event_skill_variant, event_skill_variant_desc = process_user_input(
            df=df_skills,
            attr="Variant",
            attr_desc="Variant Description",
            select_values={"Event": event, "Skill": event_skill},
            prompt=f"Enter your skill variant for {event_skill_desc}",
        )

        # get stats
        full_skill_description = (
            f"{event_skill_desc} ({event_skill_variant_desc})"
            if event_skill_variant_desc
            else event_skill_desc
        )
        print(f"Enter your skill scores for {full_skill_description}")
        for student in students:
            x = input(f"{student} >>> ")
            if x not in ["0", "1", "2", "3", "4", "5"]:
                print("Skipping student")
                continue
            skill_info = df_skills[
                (df_skills["Skill"] == event_skill)
                & (df_skills["Variant"] == event_skill_variant)
            ]
            skill_id = skill_info["Skill ID"].values[0]
            event_skill_id = skill_info["Event Skill ID"].values[0]
            status = skill_info[level].values[0]
            row = [
                period,
                event,
                event_skill,
                event_skill_variant,
                student,
                x,
                skill_id,
                event_skill_id,
                level,
                status,
            ]
            with open("output.csv", "a") as file:
                file.write(",".join(row) + "\n")

        options = {0: "no", 1: "yes"}
        options_text = "\n".join(
            f"  [{idx + 1}]: {val}" for idx, val in options.items()
        )
        x = input(f"\nWould you like to add other skill?\n{options_text}\n\n>>> ")
        if options[int(x) - 1] == "no":
            df_batch = pd.read_csv(
                "output.csv",
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
            )
            append_dataset_rows(dataset_name="experiment", df=df_batch)
            continue_data_entry = False
    if os.path.exists("output.csv"):
        os.remove("output.csv")


def process_user_input(df, attr, attr_desc, prompt, select_values=None):
    if select_values:
        conditions = [df[col] == val for col, val in select_values.items()]
        conditions.append(df[attr] != "")
        select_condition = reduce(lambda c1, c2: c1 & c2, conditions[1:], conditions[0])
        df_options = (
            df[select_condition][[attr, attr_desc]]
            .drop_duplicates()
            .reset_index(drop=True)
        )
    else:
        df_options = df[[attr, attr_desc]].drop_duplicates().reset_index(drop=True)

    df_options["display"] = df_options[attr] + " - " + df_options[attr_desc]
    options = df_options["display"].to_dict()
    value = ""
    value_desc = ""
    if options:
        options_text = "\n".join(
            f"  [{idx + 1}]: {val}" for idx, val in options.items()
        )
        x = input(f"\n{prompt}:\n{options_text}\n\n>>> ")
        value = df_options[df_options["display"] == options[int(x) - 1]][attr].values[0]
        value_desc = df_options[df_options["display"] == options[int(x) - 1]][
            attr_desc
        ].values[0]
    return value, value_desc


if __name__ == "__main__":
    source = "local"
    try:
        if sys.argv[1] == "--clear-cache":
            source = "gsheets"
    except Exception:
        pass

    df_periods, df_levels, df_events, df_skills, df_student_levels = (
        read_reference_datasets(source)
    )
    process_user_inputs(df_periods, df_levels, df_events, df_skills, df_student_levels)
