import json


def validate_dataset(df, schema):
    errors = dict()
    for name, spec in schema.items():
        # Check if column exists
        if name not in df.columns:
            message = f"Column '{name}' does not exist"
            errors[name] = errors.get(name, []) + [message]
            continue

        # Check column index
        index = spec["index"]
        _index = list(df.columns).index(name)
        if index != _index:
            message = f"Incorrect index for column '{name}': Expected {index}, Observed {_index}"
            errors[name] = errors.get(name, []) + [message]

        # Check column datatype
        dtype = spec.get("dtype", "object")
        _dtype = df.dtypes.loc[name]
        if dtype != _dtype:
            message = f"Incorrect data type for column '{name}': Expected {dtype}, Observed {_dtype}"
            errors[name] = errors.get(name, []) + [message]

        # Check column nulls
        is_nullable = spec.get("is_nullable", False)
        _isnull = df[name].isnull()
        if not is_nullable and _isnull.any():
            message = f"Column '{name}' has {int(_isnull.sum())} missing values"
            errors[name] = errors.get(name, []) + [message]

    if errors:
        message = json.dumps(errors, indent=2)
        raise Exception(f"Schema validation failed:\n{message}\n\n{df.head()}")


def standardize(df, schema):
    _df = df.copy()
    _df = _df.replace("", None)
    _df = _df.astype(
        {
            k: attr.get("dtype", "object")
            for k, attr in schema.items()
            if k in _df.columns
        }
    )
    return _df
