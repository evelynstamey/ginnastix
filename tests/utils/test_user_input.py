import builtins
from unittest import mock

import pytest

from ginnastix_class.utils.user_input import _get_input


@mock.patch.object(builtins, "input")
def test__get_input__default(m_input):
    prompt = "hi"
    m_input.return_value = "2"
    assert _get_input(prompt) == "2"
    m_input.assert_called_with("\nhi\n\n>>> ")


@pytest.mark.parametrize(
    "prompt, options, multi, user_prompt, user_input, out",
    [
        ("hi", None, False, "\nhi\n\n>>> ", "2", "2"),
        ("hi", None, True, "\nhi\n\n>>> ", "2", "2"),
        ("hi", [1, 2], False, "\nhi\n  [1]: 1\n  [2]: 2\n\n>>> ", "2", 2),
        ("hi", [1, 2], True, "\nhi\n  [1]: 1\n  [2]: 2\n\n>>> ", "2", [2]),
    ],
)
@mock.patch.object(builtins, "input")
def test__get_input__advanced(
    m_input, prompt, options, multi, user_prompt, user_input, out
):
    m_input.return_value = user_input
    assert _get_input(prompt, options=options, multi=multi) == out
    m_input.assert_called_with(user_prompt)
