DATASETS = {
    "skill_evaluation": {
        "spreadsheet_id": "1aCRvFMe0yqSaApGsuWnCl95J0YFSzpqYQEV5MRNqqjo",
        "sheet_range": "Raw",
        "columns_index": 1,
        "data_index": 2,
        "schema": {
            "Period": {"index": 0, "dtype": "object"},
            "Event": {"index": 1, "dtype": "object"},
            "Skill": {"index": 2, "dtype": "object"},
            "Variant": {
                "index": 3,
                "dtype": "object",
                "is_nullable": True,
            },
            "Athlete": {"index": 4, "dtype": "object"},
            "Score": {"index": 5, "dtype": "int"},
            "Skill ID": {"index": 6, "dtype": "object"},
            "Event Skill ID": {"index": 7, "dtype": "object"},
            "Level": {"index": 8, "dtype": "object"},
            "Status": {"index": 9, "dtype": "object"},
        },
    }
}
