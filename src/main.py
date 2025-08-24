import sys

from utils.enter_attendance import Attendance
from utils.enter_skills import SkillEvaluation

if __name__ == "__main__":
    accepted_operations = ["skill", "attendance"]
    if len(sys.argv) == 1 or sys.argv[1] not in accepted_operations:
        raise ValueError(
            f"Please supply one of the following commands: {accepted_operations}"
        )

    reference_dataset_source = "local"
    try:
        if sys.argv[2] == "--clear-cache":
            reference_dataset_source = "gsheets"
    except Exception:
        pass

    operation = sys.argv[1]
    if operation == "skill":
        se = SkillEvaluation(reference_dataset_source)
        se.add()

    if operation == "attendance":
        se = Attendance(reference_dataset_source)
        se.add()
