from unittest import mock

import numpy as np
import pandas as pd

from ginnastix_class.utils.google_sheets import _dataframe_to_gsheet_body
from ginnastix_class.utils.google_sheets import read_dataset


@mock.patch("ginnastix_class.utils.google_sheets._get_dataset_config")
@mock.patch("ginnastix_class.utils.google_sheets.get_sheet")
@mock.patch("ginnastix_class.utils.google_sheets.read_sheet_data")
def test_read_dataset(m_read_sheet_data, m_get_sheet, m__get_dataset_config):
    m__get_dataset_config.return_value = {
        "spreadsheet_id": "spreadsheet_id",
        "sheet_range": "sheet_range",
        "columns_index": 1,
        "data_index": 2,
        "schema": {
            "col0": {"index": 0, "dtype": "int"},
            "col1": {"index": 1, "dtype": "float"},
            "col2": {"index": 2},
            "col3": {"index": 3, "is_nullable": True},
        },
    }
    m_read_sheet_data.return_value = {
        "values": [
            ["nothing", "to", "see", "here"],
            ["col0", "col1", "col2", "col3"],
            [0, "0", "zero", ""],
            [1, "1", "one", ""],
        ]
    }
    expected_df = pd.DataFrame(
        [
            [0, 0.0, "zero", None],
            [1, 1.0, "one", None],
        ],
        columns=["col0", "col1", "col2", "col3"],
    )
    out_df = read_dataset(dataset_name="dataset_name", credentials="credentials")
    pd.testing.assert_frame_equal(out_df, expected_df)


def test__dataframe_to_gsheet_body():
    df = pd.DataFrame(
        {
            "col": pd.Series(
                ["1", 2.0, "three", "", pd.NaT, pd.NA, np.nan, None], dtype=object
            ),
        }
    )
    res = _dataframe_to_gsheet_body(df)
    assert res == {"values": [["1"], ["2.0"], ["three"], [""], [""], [""], [""], [""]]}
