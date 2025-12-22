import builtins
from unittest import mock

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from ginnastix_class.utils.user_input import _get_options_df
from ginnastix_class.utils.user_input import get_input
from ginnastix_class.utils.user_input import get_input_from_df


@pytest.fixture
def options_df():
    df = pd.DataFrame(
        [
            ["UB", "BHC", "x1", "back hip circle", "single", "UB_BHC[x1]", "BHC[x1]"],
            ["UB", "BHC", "x2", "back hip circle", "double", "UB_BHC[x2]", "BHC[x2]"],
            ["UB", "FHC", None, "front hip circle", None, "UB_FHC", "FHC"],
            ["BB", "BWO", None, "back walkover", None, "BB_BWO", "BWO"],
            ["FX", "BWO", None, "back walkover", None, "FX_BWO", "BWO"],
        ],
        columns=[
            "Event",
            "Skill",
            "Variant",
            "Skill Description",
            "Variant Description",
            "Skill ID",
            "Event Skill ID",
        ],
    )
    return df


@pytest.fixture
def null_options_df():
    df = pd.DataFrame(
        [
            [None, None],
            [1, None],
            [None, 2],
            ["", ""],
            [4, ""],
            ["", 5],
            [6, 6],
        ],
        columns=["attr", "attr_desc"],
    )
    return df


@mock.patch.object(builtins, "input")
def test__get_input__default(m_input):
    prompt = "hi"
    m_input.return_value = "2"
    assert get_input(prompt) == "2"
    m_input.assert_called_with("\nhi\n\n>>> ")


@pytest.mark.parametrize(
    "prompt, options, multi, user_prompt, user_input, out",
    [
        # take exact user input (no options, no multi-select)
        ("hi", None, False, "\nhi\n\n>>> ", "a", "a"),
        ("hi", None, True, "\nhi\n\n>>> ", "a", "a"),
        # ##### [list]
        # ##### user selects no option from many options
        ("hi", ["a", "b"], False, "\nhi\n  [1]: a\n  [2]: b\n\n>>> ", "", ""),
        ("hi", ["a", "b"], True, "\nhi\n  [1]: a\n  [2]: b\n\n>>> ", "", []),
        # ##### user selects one option from many options
        ("hi", ["a", "b"], False, "\nhi\n  [1]: a\n  [2]: b\n\n>>> ", "2", "b"),
        ("hi", ["a", "b"], True, "\nhi\n  [1]: a\n  [2]: b\n\n>>> ", "2", ["b"]),
        # ##### user selects many options from many options (with multi-select)
        (
            "hi",
            ["a", "b"],
            True,
            "\nhi\n  [1]: a\n  [2]: b\n\n>>> ",
            "1, 2",
            ["a", "b"],
        ),
        # ##### [dict]
        # ##### user selects no option from many options
        ("hi", {0: "a", 1: "b"}, False, "\nhi\n  [1]: a\n  [2]: b\n\n>>> ", "", ""),
        ("hi", {0: "a", 1: "b"}, True, "\nhi\n  [1]: a\n  [2]: b\n\n>>> ", "", []),
        # ##### user selects one option from many options
        ("hi", {0: "a", 1: "b"}, False, "\nhi\n  [1]: a\n  [2]: b\n\n>>> ", "2", "b"),
        ("hi", {0: "a", 1: "b"}, True, "\nhi\n  [1]: a\n  [2]: b\n\n>>> ", "2", ["b"]),
        # ##### user selects many options from many options (with multi-select)
        (
            "hi",
            {0: "a", 1: "b"},
            True,
            "\nhi\n  [1]: a\n  [2]: b\n\n>>> ",
            "1, 2",
            ["a", "b"],
        ),
    ],
)
@mock.patch.object(builtins, "input")
def test__get_input__advanced(
    m_input, prompt, options, multi, user_prompt, user_input, out
):
    m_input.return_value = user_input
    assert get_input(prompt, options=options, multi=multi) == out
    m_input.assert_called_with(user_prompt)


@pytest.mark.parametrize(
    "prompt, options, multi, user_prompt, user_input",
    [
        ("hi", {0: "a", 1: "b"}, True, "\nhi\n  [1]: a\n  [2]: b\n\n>>> ", "2,3"),
    ],
)
@mock.patch.object(builtins, "input")
def test__get_input__bad_input(
    m_input, prompt, options, multi, user_prompt, user_input
):
    m_input.return_value = user_input
    with pytest.raises(ValueError) as e:
        get_input(prompt, options=options, multi=multi)
    assert e.value.args[0] == "Aborting: Too many errors"
    assert m_input.call_count == 4


def test__get_options_df__0(options_df):
    """Give me all (distinct) events"""
    # dataframe with three rows because there are three distinct events
    expected_df = pd.DataFrame(
        [
            ["UB", "UB"],
            ["BB", "BB"],
            ["FX", "FX"],
        ],
        columns=["Event", "options"],
    )
    res = _get_options_df(options_df, "Event")
    assert_frame_equal(res, expected_df)


def test__get_options_df__1(options_df):
    """Give me all events with the skill 'BWO'"""
    # dataframe with two rows because BWO corresponds to two events
    expected_df = pd.DataFrame(
        [
            ["BB", "BB"],
            ["FX", "FX"],
        ],
        columns=["Event", "options"],
    )
    res = _get_options_df(options_df, "Event", select_values={"Skill": "BWO"})
    assert_frame_equal(res, expected_df)


def test__get_options_df__2(options_df):
    """Describe the skill code 'BHC'"""
    expected_df = pd.DataFrame(
        [
            ["BHC", "back hip circle", "BHC - back hip circle"],
        ],
        columns=["Skill", "Skill Description", "options"],
    )
    res = _get_options_df(
        options_df, "Skill", "Skill Description", select_values={"Skill": "BHC"}
    )
    assert_frame_equal(res, expected_df)


def test__get_options_df__3(options_df):
    """Give me all variants of the skill 'BHC'"""
    # dataframe with two rows because BHC has two variants
    expected_df = pd.DataFrame(
        [
            ["x1", "single", "x1 - single"],
            ["x2", "double", "x2 - double"],
        ],
        columns=["Variant", "Variant Description", "options"],
    )
    res = _get_options_df(
        options_df, "Variant", "Variant Description", select_values={"Skill": "BHC"}
    )
    assert_frame_equal(res, expected_df)


def test__get_options_df__4(options_df):
    """Give me all variants of the skill 'FHC'"""
    # empty dataframe because FHC has no variants
    expected_df = pd.DataFrame(
        [], columns=["Variant", "Variant Description", "options"]
    )
    res = _get_options_df(
        options_df, "Variant", "Variant Description", select_values={"Skill": "FHC"}
    )
    assert_frame_equal(res, expected_df, check_dtype=False)


def test__get_options_df__5(null_options_df):
    """Test null edge cases"""
    # Ignore rows with null `attr`, do not concatenate null `attr_desc`
    expected_df = pd.DataFrame(
        [
            [1, None, "1"],
            [4, "", "4"],
            [6, 6, "6 - 6"],
        ],
        columns=["attr", "attr_desc", "options"],
    )
    res = _get_options_df(null_options_df, "attr", "attr_desc")
    assert_frame_equal(res, expected_df, check_dtype=False)


@pytest.mark.parametrize(
    "user_input, out_value, out_value_desc",
    [
        ("1", 1, None),
        ("2", 4, ""),
        ("3", 6, 6),
    ],
)
@mock.patch.object(builtins, "input")
def test_get_input_from_df(
    m_input, user_input, out_value, out_value_desc, null_options_df
):
    m_input.return_value = user_input
    value, value_desc = get_input_from_df("foo", null_options_df, "attr", "attr_desc")
    assert value == out_value
    assert value_desc == out_value_desc
