import itertools
import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from ginnastix_class.utils.google_sheets import authenticate
from ginnastix_class.utils.google_sheets import read_dataset


# helpers
def get_second_highest(x):
    y = np.sort(x)
    return y[-2] if len(y) > 1 else np.nan


def upgrade_status(row):
    if all([row["Is Active?"] == "TRUE", row["Ready to Upgrade?"] == "TRUE"]):
        return "pending"

    statuses = []
    if pd.isna(row["Score #1"]):
        statuses.append("missing routine score")
    elif row["Score #1"] < 9.4:
        statuses.append("insufficient routine score")
    if pd.isna(row["Score #2"]):
        statuses.append("missing routine score")
    elif row["Score #2"] < 9.4:
        statuses.append("insufficient routine score")
    if pd.isna(row["Upgrade Skill Score"]):
        statuses.append("missing skill score")
    elif row["Upgrade Skill Score"] < 4:
        statuses.append("insufficient skill score")
    statuses.sort()
    status_summaries = []
    for key, group in itertools.groupby(statuses):
        if key.endswith("skill score"):
            status_summaries.append(key)
        else:
            if key.startswith("missing"):
                n = len(list(group))
                s = "" if n == 1 else "s"
                status_summaries.append(f"{n} missing {key[8:]}{s}")
            if key.startswith("insufficient"):
                n = len(list(group))
                s = "" if n == 1 else "s"
                status_summaries.append(f"{n} insufficient {key[13:]}{s}")
    status_summaries.sort()
    return "; ".join(status_summaries)


def read_reference_dataset(name, data_dir="data", source="gsheets", credentials=None):
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    file_name = os.path.join(data_dir, f"{name}.pkl")
    if source == "local":
        print(f"Loading local dataset from file: {file_name}")
        try:
            with open(file_name, "rb") as f:
                df = pickle.load(f)
                return df
        except Exception as e:
            print(f"Failed to load local dataset from file: {e}")

    print(f"Reading dataset from Google Sheets: {name}")
    credentials = credentials or authenticate()
    df = read_dataset(dataset_name=name, credentials=credentials)
    with open(file_name, "wb") as f:
        pickle.dump(df, f)
    return df


def main():
    ######################################################## Data
    default_routines_df = read_reference_dataset("default_routines")  # noqa
    preseason_testout_df = read_reference_dataset("preseason_testout") # noqa
    custom_routines_df = read_reference_dataset("custom_routines") # noqa
    skill_evaluation_df = read_reference_dataset("skill_evaluation")
    meet_scores_df = read_reference_dataset("meet_scores")

    ################################ TODO: Refactor "routine upgrade"
    xs_bb_ug = [("D1", "D2"), ("A1", "A2")]
    xs_ub_ug = [("D1", "D2"), ("C1", "C2")]
    xb_bb_ug = [("D1", "D2"), ("J1", "J2"), ("D2", "D3"), ("D3", "D4"), ("A1", "A2")]
    xb_ub_ug = [("D1", "D2"), ("D2", "D3")]
    routine_upgrades_df = pd.DataFrame(
        {
            "Level": ["XS"] * len(xs_bb_ug + xs_ub_ug)
            + ["XB"] * len(xb_bb_ug + xb_ub_ug),
            "Event": ["Beam"] * len(xs_bb_ug)
            + ["Bars"] * len(xs_ub_ug)
            + ["Beam"] * len(xb_bb_ug)
            + ["Bars"] * len(xb_ub_ug),
            "Event Routine": list(range(len(xs_bb_ug)))
            + list(range(len(xs_ub_ug)))
            + list(range(len(xb_bb_ug)))
            + list(range(len(xb_ub_ug))),
            "Skill to Upgrade": [i for i, _ in xs_bb_ug]
            + [i for i, _ in xs_ub_ug]
            + [i for i, _ in xb_bb_ug]
            + [i for i, _ in xb_ub_ug],
            "Upgrade Skill": [j for _, j in xs_bb_ug]
            + [j for _, j in xs_ub_ug]
            + [j for _, j in xb_bb_ug]
            + [j for _, j in xb_ub_ug],
        }
    )
    routine_upgrades_df.sort_values(["Level", "Event", "Event Routine"])

    ################################ TODO: Refactor "custom upgrades"
    custom_routine_sequence = {"Kristy": {"Bars": {0: ("D2", "D1")}}}

    ######################################################## Transform
    scores_long = pd.melt(
        meet_scores_df,
        id_vars=["Meet", "Level", "Athlete"],
        value_vars=["Beam", "Bars"],
        var_name="Event",
        value_name="Event Score",
    )
    routine_long = pd.melt(
        meet_scores_df,
        id_vars=["Meet", "Level", "Athlete"],
        value_vars=["Beam Routine", "Bars Routine"],
        var_name="Event",
        value_name="Event Routine",
    )
    routine_long["Event"] = routine_long["Event"].apply(lambda x: x.split(" ")[0])
    routine_scores_long = pd.merge(
        scores_long, routine_long, on=["Meet", "Level", "Athlete", "Event"], how="inner"
    )
    athlete_df = routine_scores_long[["Level", "Athlete"]].drop_duplicates()
    xs_athlete_routine_cross = pd.merge(
        athlete_df[athlete_df["Level"] == "XS"][["Athlete"]],
        routine_upgrades_df[routine_upgrades_df["Level"] == "XS"],
        how="cross",
    )
    xb_athlete_routine_cross = pd.merge(
        athlete_df[athlete_df["Level"] == "XB"][["Athlete"]],
        routine_upgrades_df[routine_upgrades_df["Level"] == "XB"],
        how="cross",
    )
    athlete_routine_cross = pd.concat(
        [xs_athlete_routine_cross, xb_athlete_routine_cross], axis=0
    )
    athlete_routine_cross["Custom Skill to Upgrade"] = None
    athlete_routine_cross["Custom Upgrade Skill"] = None
    athlete_routine_cross = athlete_routine_cross.rename(
        columns={
            "Skill to Upgrade": "Default Skill to Upgrade",
            "Upgrade Skill": "Default Upgrade Skill",
        }
    )
    for athlete, events in custom_routine_sequence.items():
        for event, updates in events.items():
            for routine_id, (from_skill, to_skill) in updates.items():
                athlete_routine_cross.loc[
                    (athlete_routine_cross["Athlete"] == athlete)
                    & (athlete_routine_cross["Event"] == event)
                    & (athlete_routine_cross["Event Routine"] == routine_id),
                    "Custom Skill to Upgrade",
                ] = from_skill
                athlete_routine_cross.loc[
                    (athlete_routine_cross["Athlete"] == athlete)
                    & (athlete_routine_cross["Event"] == event)
                    & (athlete_routine_cross["Event Routine"] == routine_id),
                    "Custom Upgrade Skill",
                ] = to_skill
    athlete_routine_cross["Skill to Upgrade"] = athlete_routine_cross.apply(
        lambda row: (
            row["Custom Skill to Upgrade"]
            if row["Custom Skill to Upgrade"] is not None
            else row["Default Skill to Upgrade"]
        ),
        axis=1,
    )
    athlete_routine_cross["Upgrade Skill"] = athlete_routine_cross.apply(
        lambda row: (
            row["Custom Upgrade Skill"]
            if row["Custom Upgrade Skill"] is not None
            else row["Default Upgrade Skill"]
        ),
        axis=1,
    )
    augmented_routine_scores_long = routine_scores_long.merge(
        athlete_routine_cross[
            [
                "Athlete",
                "Level",
                "Event",
                "Event Routine",
                "Skill to Upgrade",
                "Upgrade Skill",
            ]
        ],
        how="left",
        on=["Athlete", "Level", "Event", "Event Routine"],
    )

    # Create the new column using transform
    augmented_routine_scores_long["Second Highest Score"] = (
        augmented_routine_scores_long.groupby(
            ["Level", "Athlete", "Event", "Event Routine"]
        )["Event Score"].transform(get_second_highest)
    )
    filtered_routine_scores = augmented_routine_scores_long[
        (
            augmented_routine_scores_long["Event Score"]
            >= augmented_routine_scores_long["Second Highest Score"]
        )
        | augmented_routine_scores_long["Second Highest Score"].isna()
    ]
    filtered_routine_scores = filtered_routine_scores.sort_values(
        ["Level", "Athlete", "Event", "Event Routine", "Meet"]
    )
    pivoted_routine_scores = filtered_routine_scores.groupby(
        ["Level", "Athlete", "Event", "Event Routine"], as_index=False
    ).agg(
        {
            "Meet": list,
            "Event Score": list,
            "Skill to Upgrade": "first",
            "Upgrade Skill": "first",
        }
    )
    pivoted_routine_scores[["Meet #1", "Meet #2"]] = pd.DataFrame(
        pivoted_routine_scores["Meet"].tolist(), index=pivoted_routine_scores.index
    )
    pivoted_routine_scores[["Score #1", "Score #2"]] = pd.DataFrame(
        pivoted_routine_scores["Event Score"].tolist(),
        index=pivoted_routine_scores.index,
    )
    pivoted_routine_scores.drop(columns=["Meet", "Event Score"], inplace=True)
    pivoted_routine_scores["Active Routine"] = pivoted_routine_scores.groupby(
        ["Level", "Athlete", "Event"]
    )["Event Routine"].transform("max")
    pivoted_routine_scores["Baseline Routine"] = pivoted_routine_scores.groupby(
        ["Level", "Athlete", "Event"]
    )["Event Routine"].transform("min")
    pivoted_routine_scores["Is Active?"] = pivoted_routine_scores.apply(
        lambda row: "TRUE"
        if row["Event Routine"] == row["Active Routine"]
        else "FALSE",
        axis=1,
    )
    augmented_skill_eval_df = skill_evaluation_df.groupby(
        ["Level", "Athlete", "Event", "Skill ID"], as_index=False
    ).agg({"Score": "max"})
    augmented_skill_eval_df = augmented_skill_eval_df.rename(
        columns={"Skill ID": "Upgrade Skill", "Score": "Upgrade Skill Score"}
    )
    routine_and_skills_scores = pivoted_routine_scores.merge(
        augmented_skill_eval_df,
        on=["Level", "Athlete", "Event", "Upgrade Skill"],
        how="left",
    )
    routine_and_skills_scores["Ready to Upgrade?"] = routine_and_skills_scores.apply(
        lambda row: (
            "TRUE"
            if all(
                [
                    not pd.isna(row["Score #1"]),
                    not pd.isna(row["Score #2"]),
                    not pd.isna(row["Upgrade Skill Score"]),
                    row["Score #1"] >= 9.4,
                    row["Score #2"] >= 9.4,
                    row["Upgrade Skill Score"] >= 4,
                ]
            )
            else "FALSE"
        ),
        axis=1,
    )

    routine_and_skills_scores["Upgrade Status"] = routine_and_skills_scores.apply(
        upgrade_status, axis=1
    )
    routine_and_skills_scores["Admin Notes"] = ""
    routine_and_skills_scores.loc[
        (routine_and_skills_scores["Is Active?"] == "FALSE")
        & (routine_and_skills_scores["Ready to Upgrade?"] == "FALSE"),
        "Admin Notes",
    ] = "Routine was upgraded without meeting upgrade requirements. Confirm that routine and skill scores are up to date."
    return routine_and_skills_scores


if __name__ == "__main__":
    routine_and_skills_scores = main()
    print(routine_and_skills_scores)
