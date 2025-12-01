import click

from ginnastix_class.dashboard.behavior_report import main
from ginnastix_class.data_entry.enter_attendance import Attendance
from ginnastix_class.data_entry.enter_skills import SkillEvaluation


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
def behavior_report(clear_cache):
    reference_dataset_source = "gsheets" if clear_cache else "local"
    main(reference_dataset_source)
