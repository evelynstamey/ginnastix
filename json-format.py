import json
import os
import sys

IGNORE_DIRS = [".pytest_cache", ".ruff_cache", ".venv"]


def get_json_files(directory):
    """
    Recursively find all files ending with '.json' in a given directory.
    """
    json_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                json_files.append(os.path.join(root, file))
    return json_files


def format_json_file(file_path):
    file_path_parts = file_path.split(os.sep)
    if any([1 for part in file_path_parts if part in IGNORE_DIRS]):
        return False
    if os.path.dirname(file_path) in IGNORE_DIRS:
        return
    with open(file_path, "r") as f:
        data = json.load(f)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Please supply a path to a directory")
        print("")
        print("Example usage:")
        print("  python3 json-format.py .")
        print("")
        sys.exit(1)
    directory = sys.argv[1]
    json_files = get_json_files(directory)

    success = []
    skipped = []
    errors = dict()
    for file_path in json_files:
        try:
            formatted = format_json_file(file_path)
            if formatted:
                success.append(file_path)
            else:
                skipped.append(file_path)
        except Exception as e:
            errors[file_path] = e
    print(f"Successfully formatted {len(success)} JSON files")
    if errors:
        print(f"Failed to format {len(errors)} JSON files")
        for file_path, error in errors.items():
            print(f"  {file_path}: {error}")
        sys.exit(1)
