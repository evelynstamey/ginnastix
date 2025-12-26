import matplotlib.colors as mcolors
import numpy as np

VERY_BAD_COLOR = "#f04f0a"
BAD_COLOR = "#e89e1e"
OK_COLOR = "#abb53f"
GOOD_COLOR = "#208c6f"


def minmax_scaler(x, from_range=None, to_range=None, trim=False):
    """Apply min-max normalization to an array or single value."""
    _min = np.nanmin(x)
    _max = np.nanmax(x)
    from_range = from_range or (_min, _max)
    to_range = to_range or (_min, _max)

    if from_range[0] == from_range[1]:
        raise ValueError(f"Values in `from_range` must be different. Got {from_range}")

    _is_arr = True
    try:
        len(x)
    except TypeError:
        _is_arr = False

    if _is_arr:
        return [_minmax_scaler(i, from_range, to_range, trim) for i in x]
    else:
        return _minmax_scaler(x, from_range, to_range, trim)


def _minmax_scaler(x, from_range, to_range, trim):
    """Scale a number from a given range to a new range using min-max normalization.
    Ref: https://en.wikipedia.org/wiki/Feature_scaling#Rescaling_(min-max_normalization)
    """
    old_low, old_high = from_range
    new_low, new_high = to_range
    if trim:
        if x < old_low:
            x = old_low
        elif x > old_high:
            x = old_high
    return new_low + (((x - old_low) * (new_high - new_low)) / (old_high - old_low))


def rgb_arr(n, very_bad_coef=3, logspace_base=10):
    """
    Usage Note
    ----------
    Increase `very_bad_coef` and/or `logspace_base` to increase the
    proportion of "bad" colors.
    """
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "custom_linear_cmap",
        [VERY_BAD_COLOR] * very_bad_coef + [BAD_COLOR] + [OK_COLOR] + [GOOD_COLOR],
        N=n,
    )
    values = [
        cmap(i)[:3]
        for i in minmax_scaler(
            np.logspace(0, 1, n, base=logspace_base), to_range=(0, 1)
        )
    ]
    return [f"rgb({int(r * 255)},{int(g * 255)},{int(b * 255)})" for r, g, b in values]


def map_color(s):
    sample_size = len(s)
    color_indices = (
        s.fillna(0).apply(
            minmax_scaler,
            from_range=(0, 1),
            to_range=(0, sample_size - 1),
            trim=True,
        )
    ).astype(int)
    sorted_color_selection = rgb_arr(n=sample_size)
    colors = [sorted_color_selection[i] for i in color_indices]
    return colors
