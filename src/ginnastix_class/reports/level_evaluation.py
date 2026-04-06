import os
import pickle
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from ginnastix_class.utils.google_sheets import authenticate
from ginnastix_class.utils.google_sheets import read_dataset

EVENT_MAPPING = {"BB": "Beam", "VT": "Vault", "UB": "Bars", "FX": "Floor"}


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
        return str(names[0]) + " (" + str(names[1] + ")")


def process_skill_evaluations(skill_evaluation_df, skills_df, student_classes_df):
    idx = (
        skill_evaluation_df.sort_values(
            ["Period", "Inserted At"], ascending=[True, False]
        )
        .groupby(["Athlete", "Skill ID"])["Score"]
        .idxmax()
    )
    recent_skill_evaluation_df = skill_evaluation_df.loc[idx]
    athlete_skill_cross_df = pd.merge(
        skills_df[skills_df["Admin Tags"] != "internal use only"],
        pd.DataFrame(
            {
                "Athlete": student_classes_df[student_classes_df["Stop"].isna()][
                    "Student"
                ].to_list()
            }
        ),
        how="cross",
    )
    level_evaluation_df = pd.merge(
        athlete_skill_cross_df,
        recent_skill_evaluation_df[["Athlete", "Skill ID", "Score", "Period"]],
        on=["Athlete", "Skill ID"],
        how="left",
    )
    level_evaluation_df["Required Skill"] = level_evaluation_df.apply(
        skill_description, axis=1
    )
    return level_evaluation_df


def get_report_scores_df(level_evaluation_df, athlete, target_level):
    # Pretty event labels
    level_evaluation_df = level_evaluation_df.replace({"Event": EVENT_MAPPING})
    # Convert scores to integers (rounding down)
    level_evaluation_df["Score"] = (
        np.floor(level_evaluation_df["Score"]).astype(pd.Int16Dtype()).astype(object)
    )
    # filter on athlete and target level
    report_scores_df = (
        level_evaluation_df[
            (
                level_evaluation_df[target_level].isin(
                    ["*required", "*required [C]", "required"]
                )
            )
            & (level_evaluation_df["Athlete"] == athlete)
        ]
    )[["Event", "Required Skill", "Score"]]
    return report_scores_df


def get_mpl_table_df(
    report_scores_df, target_season, evaluation_date, next_evaluation, target_level
):
    threshold = 2 if target_level == "XB" else 3

    ready_for_level = None
    if report_scores_df["Score"].isnull().any():
        ready_for_level = "[ evaluation incomplete ]"
    else:
        summary = pd.cut(
            report_scores_df["Score"],
            bins=[0, threshold, 6],
            right=False,
            labels=["no", "yes"],
        ).value_counts(normalize=True)
        if summary["yes"] == 1:
            ready_for_level = "Yes"
        elif summary["yes"] >= 0.8:
            ready_for_level = "Almost!"
        else:
            ready_for_level = "Not yet"

    subheading_df = pd.DataFrame(
        [
            ["Vault", "", ""],
            ["Bars", "", ""],
            ["Beam", "", ""],
            ["Floor", "", ""],
        ],
        columns=["Event", "Required Skill", "Score"],
    )

    _df = pd.concat([report_scores_df, subheading_df], ignore_index=True)
    _df = _df.sort_values(["Event", "Required Skill"]).reset_index(drop=True)
    _row_group_idxs = _df.drop_duplicates(subset="Event").index.to_list()
    _dummy_header_df = pd.DataFrame(
        [
            ["", "", ""],
            ["", "", ""],
            ["", "", ""],
            ["TARGET SEASON", target_season, ""],
            ["EVALUATION DATE", evaluation_date, ""],
            ["", "", ""],
            ["", "", ""],
            ["", "", ""],
        ],
        columns=["Event", "Required Skill", "Score"],
    )
    _dummy_columns_df = pd.DataFrame(
        [
            ["", "Required Skill", "Score"],
        ],
        columns=["Event", "Required Skill", "Score"],
    )
    _dummy_footer_df = pd.DataFrame(
        [
            ["", "", ""],
            ["", "", ""],
            ["", "", ""],
            ["READY FOR LEVEL?", ready_for_level, ""],
            ["NEXT EVALUATION", next_evaluation, ""],
            ["", "", ""],
            ["", "", ""],
            ["", "", ""],
        ],
        columns=["Event", "Required Skill", "Score"],
    )
    df = pd.concat(
        [
            _dummy_header_df,
            _dummy_columns_df,
            _df,
            _dummy_footer_df,
        ],
        ignore_index=True,
    ).reset_index(drop=True)
    header_start_idx = 0
    column_idx = header_start_idx + len(_dummy_header_df)
    body_start_idx = column_idx + len(_dummy_columns_df)
    footer_start_idx = body_start_idx + len(_df)
    row_group_idxs = [
        i + len(_dummy_header_df) + len(_dummy_columns_df) for i in _row_group_idxs
    ]
    nrows = len(df)
    df_stats = {
        "header_start_idx": header_start_idx,
        "column_idx": column_idx,
        "body_start_idx": body_start_idx,
        "footer_start_idx": footer_start_idx,
        "row_group_idxs": row_group_idxs,
        "nrows": nrows,
    }
    return df, df_stats


def export_df_to_pdf(
    df,
    df_stats,
    athlete,
    target_level,
    filename,
    fig_height_scale_factor=4.5,
    cell_height_scale_factor=1.2,
    title_height=1.11,
):
    cell_height = cell_height_scale_factor / df_stats["nrows"]
    fig_height = df_stats["nrows"] / fig_height_scale_factor

    fig, ax = plt.subplots(figsize=(6, fig_height))
    ax.set_title(athlete, y=title_height, loc="left", fontsize=20)
    subtitle_height = title_height - (title_height * cell_height)
    ax.text(
        0,
        subtitle_height,
        f"Level Evaluation | {target_level}",
        transform=ax.transAxes,
        ha="left",
        fontsize=12,
        fontweight="bold",
    )
    ax.axis("tight")
    ax.axis("off")
    cell_colors = [
        (["lightgray"] * 3) if row in df_stats["row_group_idxs"] else (["white"] * 3)
        for row in range(df_stats["nrows"])
    ]
    the_table = ax.table(
        cellText=df.values,
        cellColours=cell_colors,
        loc="center",
        colWidths=[0.4, 0.45, 0.15],
    )
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(8)
    for (row, col), cell in the_table.get_celld().items():
        cell.get_text().set_verticalalignment("center")
        cell.set_height(cell_height)
        cell.set_linewidth(0)
        # format header
        if (
            row > df_stats["header_start_idx"] + 2
            and row <= df_stats["header_start_idx"] + 4
        ):
            if col == 0:
                cell.get_text().set_horizontalalignment("left")
                cell.set_facecolor("lightgray")
                cell.set_text_props(fontweight="bold")
            if col > 0:
                cell.get_text().set_horizontalalignment("left")
                cell.set_facecolor("#f0f0f0")
        # format main table columns
        if row >= df_stats["column_idx"] and row < df_stats["body_start_idx"]:
            cell.set_text_props(fontweight="bold")
            if col == 1:
                cell.get_text().set_horizontalalignment("right")
            elif col == 2:
                cell.get_text().set_horizontalalignment("center")
        # Format main table
        if row >= df_stats["body_start_idx"] and row < df_stats["footer_start_idx"]:
            # format "Event" names
            if col == 0:
                cell.get_text().set_horizontalalignment("left")
                if row not in df_stats["row_group_idxs"]:
                    cell.set(visible=False)
                elif row in df_stats["row_group_idxs"]:
                    cell.set_text_props(fontweight="bold")
            # format "Score" values
            if col == 2:
                cell.get_text().set_horizontalalignment("center")
                if cell.get_text().get_text() == "<NA>":
                    cell.set(visible=False)
                try:
                    score = float(cell.get_text().get_text())
                except Exception:
                    score = -99
                if score >= 3:
                    cell.set_text_props(color="#478f0b")
                    cell.set_facecolor("#f6ffd4")
                elif score < 3 and score >= 0:
                    cell.set_text_props(color="#e65c2e")
                    cell.set_facecolor("#ffede8")

        # format Footer
        if (
            row > df_stats["footer_start_idx"] + 2
            and row <= df_stats["footer_start_idx"] + 4
        ):
            if col == 0:
                cell.get_text().set_horizontalalignment("left")
                cell.set_facecolor("lightgray")
                cell.set_text_props(fontweight="bold")
            if col > 0:
                cell.get_text().set_horizontalalignment("left")
                cell.set_facecolor("#f0f0f0")

    with PdfPages(filename) as pdf:
        print(f"Writing report to: {filename}")
        pdf.savefig(fig, bbox_inches="tight", pad_inches=0.5)
    plt.close()


def generate_reports(
    target_season,
    evaluation_date,
    next_evaluation,
    target_directory="level_evaluations",
):
    skill_evaluation_df = read_reference_dataset("skill_evaluation")
    skills_df = read_reference_dataset("skills_v2")
    student_classes_df = read_reference_dataset("student_classes")

    level_evaluation_df = process_skill_evaluations(
        skill_evaluation_df, skills_df, student_classes_df
    )
    athletes = level_evaluation_df["Athlete"].unique()
    target_levels = ["XB", "XS", "XG"]

    for athlete in athletes:
        for target_level in target_levels:
            report_scores_df = get_report_scores_df(
                level_evaluation_df, athlete=athlete, target_level=target_level
            )
            _evaluation_date = evaluation_date.lower().replace(" ", "_")
            _athlete = athlete.lower().replace(" ", "_")
            dir = os.path.join(
                target_directory, target_season, _athlete, _evaluation_date
            )
            path = Path(dir)
            path.mkdir(parents=True, exist_ok=True)
            df, df_stats = get_mpl_table_df(
                report_scores_df,
                target_season=target_season,
                evaluation_date=evaluation_date,
                next_evaluation=next_evaluation,
                target_level=target_level,
            )
            _file_name = f"{_athlete}__{target_season}_{target_level.lower()}.pdf"
            export_df_to_pdf(
                df=df,
                df_stats=df_stats,
                athlete=athlete,
                target_level=target_level,
                filename=os.path.join(dir, _file_name),
            )
