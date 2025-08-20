DATASETS = {
    "periods": {
        "spreadsheet_id": "1ir39WGL9GD35PHEbntNIjlxPswx6H9AtYwm5r0EETLA",
        "sheet_range": "Periods",
        "schema": {
            "Period": {"index": 0},
        },
    },
    "levels": {
        "spreadsheet_id": "1ir39WGL9GD35PHEbntNIjlxPswx6H9AtYwm5r0EETLA",
        "sheet_range": "Levels",
        "schema": {
            "Level": {"index": 0},
            "Level Description": {"index": 1},
        },
    },
    "events": {
        "spreadsheet_id": "1ir39WGL9GD35PHEbntNIjlxPswx6H9AtYwm5r0EETLA",
        "sheet_range": "Events",
        "schema": {
            "Event": {"index": 0},
            "Event Description": {"index": 1},
        },
    },
    "skills": {
        "spreadsheet_id": "1ir39WGL9GD35PHEbntNIjlxPswx6H9AtYwm5r0EETLA",
        "sheet_range": "Skills",
        "schema": {
            "Event": {"index": 0},
            "Skill": {"index": 1},
            "Variant": {"index": 2},
            "Skill Description": {"index": 3},
            "Variant Description": {"index": 4},
            "Skill ID": {"index": 5},
            "Event Skill ID": {"index": 6},
            "XB": {"index": 7},
            "XS": {"index": 8},
            "XG": {"index": 9},
        },
    },
    "students": {
        "spreadsheet_id": "1ir39WGL9GD35PHEbntNIjlxPswx6H9AtYwm5r0EETLA",
        "sheet_range": "Students",
        "schema": {
            "Student": {"index": 0},
            "DOB": {"index": 1},
            "Current Age": {"index": 2, "dtype": "float"},
            "Is Active": {"index": 3},  # TODO: handle boolean types
        },
    },
    "student_levels": {
        "spreadsheet_id": "1ir39WGL9GD35PHEbntNIjlxPswx6H9AtYwm5r0EETLA",
        "sheet_range": "Student Levels",
        "schema": {
            "Student": {"index": 0},
            "Level": {"index": 1},
            "Season": {"index": 2},
        },
    },
    "skill_evaluation": {
        "spreadsheet_id": "1ir39WGL9GD35PHEbntNIjlxPswx6H9AtYwm5r0EETLA",
        "sheet_range": "Skill Evaluation",
        "schema": {
            "Period": {"index": 0},
            "Event": {"index": 1},
            "Skill": {"index": 2},
            "Variant": {"index": 3, "is_nullable": True},
            "Athlete": {"index": 4},
            "Score": {"index": 5, "dtype": "int"},
            "Skill ID": {"index": 6},
            "Event Skill ID": {"index": 7},
            "Level": {"index": 8},
            "Status": {"index": 9},
            "Inserted At": {"index": 10},
        },
    },
}
