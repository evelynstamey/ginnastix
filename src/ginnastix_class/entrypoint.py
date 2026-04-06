import os
from datetime import datetime

import click

from ginnastix_class.dashboard.behavior_report.main import main
from ginnastix_class.data_entry.enter_attendance import Attendance
from ginnastix_class.data_entry.enter_skills import SkillEvaluation
from ginnastix_class.reports.level_evaluation import generate_reports


@click.group()
def cli():
    pass


@cli.command()
@click.option("--clear-cache", is_flag=True)
def skills(clear_cache):
    reference_dataset_source = "gsheets" if clear_cache else "local"
    skill_evaluation = SkillEvaluation(reference_dataset_source)
    skill_evaluation.add()


@cli.command()
@click.option("--clear-cache", is_flag=True)
@click.option("--resume-data-entry", is_flag=True)
def attendance(clear_cache, resume_data_entry):
    reference_dataset_source = "gsheets" if clear_cache else "local"
    attendance = Attendance(reference_dataset_source, resume_data_entry)
    attendance.add()


@cli.command()
@click.option("--clear-cache", is_flag=True)
@click.option("--debug", is_flag=True)
def behavior_report(clear_cache, debug):
    reference_dataset_source = "gsheets" if clear_cache else "local"
    main(reference_dataset_source, debug)


@cli.command()
@click.option(
    "--target-directory",
    default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "level_evaluations"
    ),
)
def level_evaluation(target_directory):
    right_now = datetime.now()
    current_year = right_now.year
    current_month = right_now.month
    target_season = current_year + 1
    if current_month in [1, 2, 3, 4]:
        next_eval_month = 5
        next_eval_year = current_year
    elif current_month in [5, 6, 7]:
        next_eval_month = 8
        next_eval_year = current_year
    else:
        next_eval_month = 5
        next_eval_year = current_year + 1

    target_season = str(target_season)
    evaluation_date = right_now.strftime("%B %Y")
    next_evaluation = datetime(next_eval_year, next_eval_month, 1).strftime("%B %Y")
    generate_reports(target_season, evaluation_date, next_evaluation, target_directory)
