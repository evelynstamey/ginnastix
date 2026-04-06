import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from ginnastix_class.utils.google_sheets import authenticate
from ginnastix_class.utils.google_sheets import read_dataset
from ginnastix_class.utils.google_sheets import truncate_reload_dataset_rows


# helpers
def get_second_highest(x):
    y = np.sort(x)
    return y[-2] if len(y) > 1 else np.nan


def score_status(x, threshold):
    if pd.isna(x):
        return "missing"
    if x < threshold:
        return "insufficient"
    return "done"


def upgrade_status(row):
    if row["Is Active?"] == "FALSE":
        return "complete"

    if all(
        [
            row["Meet Score Status #1"] == "done",
            row["Meet Score Status #2"] == "done",
            row["Skill Score Status"] == "done",
        ]
    ):
        return "ready"

    if all(
        [
            row["Meet Score Status #1"] == "done",
            row["Meet Score Status #2"] == "done",
        ]
    ):
        return "awaiting skill"

    if all(
        [
            row["Skill Score Status"] == "done",
        ]
    ):
        return "awaiting routine"

    if all(
        [
            row["Meet Score Status #1"] == "missing",
            row["Meet Score Status #2"] == "missing",
            row["Skill Score Status"] == "missing",
        ]
    ):
        return "not started"
    else:
        return "in progress"


def ready_to_upgrade(row):
    if all(
        [
            row["Meet Score Status #1"] == "done",
            row["Meet Score Status #2"] == "done",
            row["Skill Score Status"] == "done",
        ]
    ):
        return "TRUE"
    return "FALSE"


def read_reference_dataset(name, data_dir="data", source="gsheet", credentials=None):
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


def skill_description(s):
    ignore = [None, ""]
    names = [s["Skill Description"], s["Variant Description"]]
    if names[1] in ignore:
        return str(names[0])
    else:
        return str(names[0]) + " - " + str(names[1])


def main():
    ######################################################## Data
    # Raw datasets
    EVENT_MAPPING = {"BB": "Beam", "VT": "Vault", "UB": "Bars", "FX": "Floor"}
    levels_df = read_reference_dataset("levels")
    default_routines_df = read_reference_dataset("default_routines")
    preseason_testout_df = read_reference_dataset("preseason_testout")
    custom_routines_df = read_reference_dataset("custom_routines")
    skill_evaluation_df = read_reference_dataset("skill_evaluation")
    skills_df = read_reference_dataset("skills_v2")  # noqa
    meet_scores_df = read_reference_dataset("meet_scores")

    # Derived datasets
    athlete_df = meet_scores_df[["Level", "Athlete"]].drop_duplicates()

    ######################################################## Transform
    # Get all default athlete routines
    _athlete_routines_dfs = []
    for level in levels_df["Level"]:
        _athlete_routines_dfs.append(
            pd.merge(
                athlete_df[athlete_df["Level"] == level][["Athlete"]],
                default_routines_df[default_routines_df["Level"] == level],
                how="cross",
            )
        )
    athlete_routines_df = pd.concat(_athlete_routines_dfs, axis=0, ignore_index=True)

    # Patch default routines with custom routines
    athlete_routines_df.rename(
        columns={"Default Upgrade Order": "Upgrade Order"}, inplace=True
    )
    custom_routines_df.rename(
        columns={"Custom Upgrade Order": "Upgrade Order"}, inplace=True
    )
    custom_routines_df.drop(columns="Notes", inplace=True)
    for (
        _athlete,
        _event,
        _level,
    ), _custom_athlete_routines_df in custom_routines_df.groupby(
        ["Athlete", "Level", "Event"]
    ):
        _default_athlete_routines_df = athlete_routines_df[
            (athlete_routines_df["Athlete"] == _athlete)
            & (athlete_routines_df["Level"] == _event)
            & (athlete_routines_df["Event"] == _level)
        ]
        _indices_to_drop = _default_athlete_routines_df.index
        athlete_routines_df.drop(_indices_to_drop, inplace=True)
        athlete_routines_df = pd.concat(
            [athlete_routines_df, _custom_athlete_routines_df],
            axis=0,
            ignore_index=True,
        )

    # Patch default routines with preseason test-outs
    for (_athlete, _event, _level), _testout_skills_df in preseason_testout_df.groupby(
        ["Athlete", "Level", "Event"]
    ):
        _testout_skills = _testout_skills_df["Skill ID"].to_list()
        _athlete_routines_df = athlete_routines_df[
            (athlete_routines_df["Athlete"] == _athlete)
            & (athlete_routines_df["Level"] == _event)
            & (athlete_routines_df["Event"] == _level)
        ].copy()
        _indices_to_drop = _athlete_routines_df.index

        _athlete_routines_df["_idx"] = _athlete_routines_df.apply(
            lambda row: (
                pd.NA
                if row["Skill ID"] in _testout_skills
                else row["Skill Rank In Category"]
            ),
            axis=1,
        )
        _athlete_routines_df["_idx_min"] = _athlete_routines_df.groupby(
            ["Level", "Event", "Routine Skill Category ID"]
        )["_idx"].transform("min")
        _athlete_routines_df["_idx_diff"] = (
            _athlete_routines_df["_idx"] - _athlete_routines_df["_idx_min"]
        )

        _athlete_routines_df["_testout_upgrade_order"] = _athlete_routines_df.apply(
            lambda row: (
                row["Upgrade Order"]
                if not pd.isna(row["_idx_diff"]) and row["_idx_diff"] > 0
                else row["_idx_diff"]
            ),
            axis=1,
        )
        _athlete_routines_df["_testout_upgrade_order"] = (
            _athlete_routines_df["_testout_upgrade_order"].rank(method="dense") - 1
        ).astype(pd.Int32Dtype())

        _athlete_routines_df.drop(columns="Upgrade Order", inplace=True)
        _athlete_routines_df.rename(
            columns={"_testout_upgrade_order": "Upgrade Order"}, inplace=True
        )
        _athlete_routines_df = _athlete_routines_df[
            [c for c in _athlete_routines_df.columns if not c.startswith("_")]
        ]

        athlete_routines_df.drop(_indices_to_drop, inplace=True)
        athlete_routines_df = pd.concat(
            [athlete_routines_df, _athlete_routines_df], axis=0, ignore_index=True
        )

    # Reshape scores
    scores_long = pd.melt(
        meet_scores_df,
        id_vars=["Meet", "Level", "Athlete"],
        value_vars=list(EVENT_MAPPING.values()),
        var_name="Event",
        value_name="Event Score",
    )
    routine_long = pd.melt(
        meet_scores_df,
        id_vars=["Meet", "Level", "Athlete"],
        value_vars=[f"{i} Routine" for i in list(EVENT_MAPPING.values())],
        var_name="Event",
        value_name="Event Routine",
    )
    routine_long["Event"] = routine_long["Event"].apply(lambda x: x.split(" ")[0])
    routine_scores_long = pd.merge(
        scores_long, routine_long, on=["Meet", "Level", "Athlete", "Event"], how="inner"
    )

    # Make "current" and "upgrade" skill pairs for each routine
    athlete_routines_df["_has_zero_skill"] = athlete_routines_df.groupby(
        ["Athlete", "Level", "Event", "Routine Skill Category ID"]
    )["Upgrade Order"].transform(
        lambda x: any([i == 1 if not pd.isna(i) else False for i in x])
    )

    drop_records_df = athlete_routines_df[
        (
            (athlete_routines_df["Upgrade Order"] == 0)
            & ~(athlete_routines_df["_has_zero_skill"])
        )
        | (athlete_routines_df["Upgrade Order"].isna())
    ]
    simplified_df = athlete_routines_df.drop(drop_records_df.index).reset_index(
        drop=True
    )
    simplified_df["n+1"] = simplified_df["Upgrade Order"] + 1

    simplified_df = pd.merge(
        simplified_df,
        skills_df[["Skill ID", "Skill Description", "Variant Description"]],
        on="Skill ID",
        how="left",
    )
    simplified_df["Skill Name"] = simplified_df.apply(skill_description, axis=1)

    skill_pairs_df = (
        pd.merge(
            simplified_df[
                [
                    "Athlete",
                    "Level",
                    "Event",
                    "Upgrade Order",
                    "n+1",
                    "Skill ID",
                    "Skill Name",
                ]
            ],
            simplified_df[
                [
                    "Athlete",
                    "Level",
                    "Event",
                    "Upgrade Order",
                    "n+1",
                    "Skill ID",
                    "Skill Name",
                ]
            ],
            right_on=["Athlete", "Level", "Event", "Upgrade Order"],
            left_on=["Athlete", "Level", "Event", "n+1"],
            how="left",
            suffixes=("", "+1"),
        )
        .sort_values(["Athlete", "Level", "Event", "Upgrade Order"])
        .reset_index(drop=True)
    )

    skill_pairs_df = skill_pairs_df[
        [
            "Athlete",
            "Level",
            "Event",
            "Upgrade Order",
            "Skill ID",
            "Skill Name",
            "Skill ID+1",
            "Skill Name+1",
        ]
    ]
    skill_pairs_df.rename(
        columns={
            "Upgrade Order": "Event Routine",
            "Skill Name": "Current Skill",
            "Skill Name+1": "Upgrade Skill",
            "Skill ID": "Current Skill ID",
            "Skill ID+1": "Upgrade Skill ID",
        },
        inplace=True,
    )

    # Join scores and skills
    scores_and_skills_df = routine_scores_long.merge(
        skill_pairs_df[
            [
                "Athlete",
                "Level",
                "Event",
                "Event Routine",
                "Current Skill",
                "Upgrade Skill",
                "Current Skill ID",
                "Upgrade Skill ID",
            ]
        ],
        how="left",
        on=["Athlete", "Level", "Event", "Event Routine"],
    )

    scores_and_skills_df["Second Highest Score"] = scores_and_skills_df.groupby(
        ["Level", "Athlete", "Event", "Event Routine"]
    )["Event Score"].transform(get_second_highest)
    filtered_routine_scores = scores_and_skills_df[
        (
            scores_and_skills_df["Event Score"]
            >= scores_and_skills_df["Second Highest Score"]
        )
        | scores_and_skills_df["Second Highest Score"].isna()
    ]
    filtered_routine_scores = filtered_routine_scores.sort_values(
        ["Level", "Athlete", "Event", "Event Routine", "Event Score", "Meet"],
        ascending=[True, True, True, True, False, False],
    )
    pivoted_routine_scores = filtered_routine_scores.groupby(
        ["Level", "Athlete", "Event", "Event Routine"], as_index=False
    ).agg(
        {
            "Meet": list,
            "Event Score": list,
            "Current Skill": "first",
            "Upgrade Skill": "first",
            "Current Skill ID": "first",
            "Upgrade Skill ID": "first",
        }
    )
    pivoted_routine_scores[["Meet #1", "Meet #2"]] = pd.DataFrame(
        pivoted_routine_scores["Meet"].tolist(), index=pivoted_routine_scores.index
    )[[0, 1]]
    pivoted_routine_scores[["Meet Score #1", "Meet Score #2"]] = pd.DataFrame(
        pivoted_routine_scores["Event Score"].tolist(),
        index=pivoted_routine_scores.index,
    )[[0, 1]]
    pivoted_routine_scores.drop(columns=["Meet", "Event Score"], inplace=True)
    pivoted_routine_scores["Active Routine"] = pivoted_routine_scores.groupby(
        ["Level", "Athlete", "Event"]
    )["Event Routine"].transform("max")
    pivoted_routine_scores["Is Active?"] = pivoted_routine_scores.apply(
        lambda row: (
            "TRUE" if row["Event Routine"] == row["Active Routine"] else "FALSE"
        ),
        axis=1,
    )

    # Augment with analytics
    augmented_skill_eval_df = skill_evaluation_df.groupby(
        ["Level", "Athlete", "Event", "Skill ID"], as_index=False
    ).agg({"Score": "max"})
    augmented_skill_eval_df = augmented_skill_eval_df.rename(
        columns={"Skill ID": "Upgrade Skill ID", "Score": "Skill Score"}
    )
    augmented_skill_eval_df = augmented_skill_eval_df.replace({"Event": EVENT_MAPPING})

    scores_summary = pivoted_routine_scores.merge(
        augmented_skill_eval_df,
        on=["Level", "Athlete", "Event", "Upgrade Skill ID"],
        how="left",
    )

    scores_summary["Meet Score Status #1"] = scores_summary["Meet Score #1"].apply(
        score_status, threshold=9.4
    )
    scores_summary["Meet Score Status #2"] = scores_summary["Meet Score #2"].apply(
        score_status, threshold=9.4
    )
    scores_summary["Skill Score Status"] = scores_summary["Skill Score"].apply(
        score_status, threshold=4
    )
    scores_summary["Upgrade Status"] = scores_summary.apply(upgrade_status, axis=1)
    scores_summary["Ready to Upgrade?"] = scores_summary.apply(ready_to_upgrade, axis=1)
    scores_summary["Admin Notes"] = ""
    scores_summary.loc[
        (scores_summary["Is Active?"] == "FALSE")
        & (scores_summary["Ready to Upgrade?"] == "FALSE"),
        "Admin Notes",
    ] = "Routine was upgraded without meeting upgrade requirements. Confirm that routine and skill scores are up to date."

    scores_summary = (
        scores_summary[
            [
                "Level",
                "Athlete",
                "Event",
                "Event Routine",
                "Current Skill",
                "Upgrade Skill",
                "Skill Score",
                "Meet #1",
                "Meet Score #1",
                "Meet #2",
                "Meet Score #2",
                "Is Active?",
                "Ready to Upgrade?",
                "Skill Score Status",
                "Meet Score Status #1",
                "Meet Score Status #2",
                "Upgrade Status",
                "Admin Notes",
            ]
        ]
        .sort_values(["Level", "Athlete", "Event", "Event Routine"])
        .reset_index(drop=True)
    )
    scores_summary["Upgrade Skill"] = scores_summary["Upgrade Skill"].fillna("[none]")

    return scores_summary


if __name__ == "__main__":
    scores_summary = main()
    truncate_reload_dataset_rows(dataset_name="upgrade_tracker", df=scores_summary)
