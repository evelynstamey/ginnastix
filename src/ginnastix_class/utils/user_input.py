def get_input(prompt, options=None, multi=False):
    while True:
        try:
            return _get_input(prompt, options, multi)
        except Exception as e:
            print(f"Invalid input ({e})")


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

    if multi:
        if x:
            return [options[int(i) - 1] for i in x.split(",")]
        else:
            return []
    else:
        if x:
            return options[int(x) - 1]
        else:
            return ""


def get_input2(prompt, options=None, multi=False):
    if not options:
        return input(f"\n{prompt}\n\n>>> ")
    options_text = "\n".join(f"  [{idx + 1}]: {val}" for idx, val in options.items())
    x = input(f"\n{prompt}\n{options_text}\n\n>>> ")
    if multi:
        return [options[int(i) - 1] for i in x.split(",")]
    else:
        return options[int(x) - 1]
