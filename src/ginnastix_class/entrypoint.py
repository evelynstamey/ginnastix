import os
from datetime import datetime

import click

from ginnastix_class.dashboard.behavior_report.main import run_behavior_report
from ginnastix_class.data_entry.enter_attendance import Attendance
from ginnastix_class.data_entry.enter_skills import SkillEvaluation
from ginnastix_class.reports.level_evaluation import generate_reports
from ginnastix_class.reports.upgrade_tracker import run_upgrade_tracker


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
    run_behavior_report(reference_dataset_source, debug)


@cli.command()
@click.option(
    "--target-directory",
    default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "level_evaluations"
    ),
)
@click.option(
    "--evaluation-date",
    default=datetime.now().strftime("%Y-%m-%d"),
    help="Optional evaluation reference date for generating historical evaluations post hoc",
)
@click.option("--athlete-name", default=None, help="Only process one athlete")
def level_evaluation(target_directory, evaluation_date, athlete_name):
    evaluation_dt = datetime.strptime(evaluation_date, "%Y-%m-%d")
    generate_reports(evaluation_dt, target_directory, athlete_name)


@cli.command()
def upgrade_tracker():
    run_upgrade_tracker()
