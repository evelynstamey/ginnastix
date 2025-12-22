import numpy as np
import pandas as pd
import pytest

from ginnastix_class.utils.validation import standardize
from ginnastix_class.utils.validation import validate_dataset


def test_validate_dataset__missing_column():
    schema = {"col": {"index": 0}}
    invalid_df = pd.DataFrame()
    with pytest.raises(Exception) as e:
        validate_dataset(invalid_df, schema)
    assert "Column 'col' does not exist" in str(e.value)


def test_validate_dataset__bad_column_order():
    schema = {"col_0": {"index": 1}, "col_1": {"index": 0}}
    invalid_df = pd.DataFrame(columns=["col_0", "col_1"])
    with pytest.raises(Exception) as e:
        validate_dataset(invalid_df, schema)
    assert "Incorrect index for column 'col_0': Expected 1, Observed 0" in str(e.value)
    assert "Incorrect index for column 'col_1': Expected 0, Observed 1" in str(e.value)


def test_validate_dataset__bad_datatype():
    schema = {"col_int": {"index": 0, "dtype": "int"}, "col_obj": {"index": 1}}
    invalid_df = pd.DataFrame(
        {
            "col_int": pd.Series([1], dtype=object),
            "col_obj": pd.Series(["1"], dtype=int),
        }
    )
    with pytest.raises(Exception) as e:
        validate_dataset(invalid_df, schema)
    assert (
        "Incorrect data type for column 'col_int': Expected int, Observed object"
        in str(e.value)
    )
    assert (
        "Incorrect data type for column 'col_obj': Expected object, Observed int64"
        in str(e.value)
    )


def test_validate_dataset__non_nullable_object():
    schema = {"col": {"index": 0}}
    valid_df = pd.DataFrame(
        {
            "col": pd.Series(["1", 2.0, "three", ""], dtype=object),
        }
    )
    validate_dataset(valid_df, schema)

    invalid_df = pd.DataFrame(
        {
            "col": pd.Series([pd.NaT, pd.NA, np.nan, None], dtype=object),
        }
    )
    with pytest.raises(Exception) as e:
        validate_dataset(invalid_df, schema)
    assert "Column 'col' has 4 missing values" in str(e.value)


def test_validate_dataset__nullable_object():
    schema = {"col": {"index": 0, "is_nullable": True}}
    valid_df = pd.DataFrame(
        {
            "col": pd.Series(
                ["1", 2.0, "three", "", pd.NaT, pd.NA, np.nan, None], dtype=object
            ),
        }
    )
    validate_dataset(valid_df, schema)


def test_validate_dataset__non_nullable_float():
    schema = {"col": {"index": 0, "dtype": "float"}}
    valid_df = pd.DataFrame(
        {
            "col": pd.Series([1, 2.0, "1"], dtype=float),
        }
    )
    validate_dataset(valid_df, schema)

    invalid_df = pd.DataFrame(
        {
            "col": pd.Series([np.nan, None], dtype=float),
        }
    )
    with pytest.raises(Exception) as e:
        validate_dataset(invalid_df, schema)
    assert "Column 'col' has 2 missing values" in str(e.value)


def test_validate_dataset__nullable_float():
    schema = {
        "col": {
            "index": 0,
            "is_nullable": True,
            "dtype": "Float32",
        }
    }
    valid_df = pd.DataFrame(
        {
            "col": pd.Series(
                [1, 2.0, "1", pd.NA, np.nan, None],
                dtype=pd.Float32Dtype(),
            ),
        }
    )
    validate_dataset(valid_df, schema)

    # Even though Pandas supports missing values in nullable columns
    # our application requires the "is_nullable" flag to be set to True
    # in order to accept nulls. Note that "is_nullable" defaults to False
    # when not explicitly set.
    schema = {"col": {"index": 0, "is_nullable": False, "dtype": "Float32"}}
    invalid_df = valid_df.copy()
    with pytest.raises(Exception) as e:
        validate_dataset(invalid_df, schema)
    assert "Column 'col' has 3 missing values" in str(e.value)


def test_standardize():
    schema = {
        "object": {},
        "nullable_float": {"dtype": "Float32"},
    }
    in_df = pd.DataFrame(
        {
            "object": pd.Series(["0", "", np.nan], dtype=object),
            "nullable_float": pd.Series(["0", "1.5", np.nan], dtype=object),
        }
    )

    # converts "" to None and casts to configured dtypes
    expected_df = pd.DataFrame(
        {
            "object": pd.Series(["0", None, np.nan], dtype=object),
            "nullable_float": pd.Series([0, 1.5, np.nan], dtype=pd.Float32Dtype()),
        }
    )
    out_df = standardize(in_df, schema)
    pd.testing.assert_frame_equal(out_df, expected_df)
