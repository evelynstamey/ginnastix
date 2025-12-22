from functools import reduce


def get_input(prompt, options=None, multi=False):
    attempt = 0
    while attempt < 4:
        if attempt > 0:
            print("Please try again")
        try:
            return _get_input(prompt, options, multi)
        except Exception as e:
            print(f"Could not process input ({e})")
            attempt += 1
    raise ValueError("Aborting: Too many errors")


def _get_input(prompt, options=None, multi=False):
    if options is None:
        return input(f"\n{prompt}\n\n>>> ")

    if isinstance(options, dict):
        options_text = "\n".join(
            f"  [{idx + 1}]: {val}" for idx, val in options.items()
        )
    else:
        options_text = "\n".join(
            f"  [{idx + 1}]: {val}" for idx, val in enumerate(options)
        )

    x = None
    if options_text:
        x = input(f"\n{prompt}\n{options_text}\n\n>>> ")

    try:
        if multi:
            if x:
                return [options[int(i.strip()) - 1] for i in x.split(",")]
            else:
                return []
        else:
            if x:
                return options[int(x.strip()) - 1]
            else:
                return ""
    except Exception as e:
        raise ValueError(f"Invalid input: {x}") from e


def get_input_from_df(prompt, df, attr, attr_desc=None, select_values=None):
    df_options = _get_options_df(df, attr, attr_desc, select_values)
    options = df_options["options"].to_dict()
    value = None
    value_desc = None
    if options:
        _input = get_input(prompt, options, multi=False)
        df_selected_option = df_options[df_options["options"] == _input]
        value = df_selected_option[attr].values[0]
        if attr_desc:
            value_desc = df_selected_option[attr_desc].values[0]
    return value, value_desc


def _get_options_df(df, attr, attr_desc=None, select_values=None):
    _df = df.copy()

    # Define row selection criteria (ignore nulls and filter on specified values)
    conditions = [(~_df[attr].isnull()), (_df[attr] != "")]
    if select_values:
        conditions.extend([_df[col] == val for col, val in select_values.items()])
    select_condition = reduce(lambda c1, c2: c1 & c2, conditions[1:], conditions[0])
    _cols = [attr, attr_desc] if attr_desc else [attr]
    _df = _df[select_condition][_cols].drop_duplicates().reset_index(drop=True)

    # Construct user-friendly option name
    _df["options"] = _df.apply(_get_option_name, axis=1)

    return _df


def _get_option_name(s):
    ignore = [None, ""]
    if len(s) == 1:
        return str(s.iloc[0])
    elif len(s) == 2:
        if s.iloc[1] in ignore:
            return str(s.iloc[0])
        else:
            return str(s.iloc[0]) + " - " + str(s.iloc[1])
    else:
        raise ValueError(f"Unexpected tuple: {s}")
