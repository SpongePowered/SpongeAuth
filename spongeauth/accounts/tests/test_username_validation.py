import django.core.exceptions

import pytest

import accounts.models
import accounts.tests.factories


BAD_EXAMPLES = [
    ("lukegb", []),
    ("_lukegb", []),
    ("_lukegb_", []),
    ("a", ['username_min_length']),
    ("__", ['username_double_special', 'username_min_length']),
    ("._", ['username_double_special', 'username_min_length', 'username_charset', 'username_initial_charset']),
    ("\N{SNOWMAN}", ['username_charset', 'username_min_length', 'username_ending_charset', 'username_initial_charset']),
    (".png", ['username_charset', 'username_initial_charset']),
    ("lukegb.png", ['username_charset']),
    ("luke__gb", ['username_double_special']),
    ("luke_.gb", ['username_charset', 'username_double_special']),
    ("lukegb-", ['username_ending_charset']),
    ("-lukegb", ['username_initial_charset']),
]


@pytest.mark.parametrize("test_input,expected", BAD_EXAMPLES)
def test_validate_username(test_input, expected):
    got = set()
    try:
        accounts.models.validate_username(test_input)
    except django.core.exceptions.ValidationError as err:
        for suberr in err.error_list:
            got.add(suberr.code)
    assert got == set(expected)


@pytest.mark.parametrize("test_input,expected", BAD_EXAMPLES)
def test_validate_username_model(test_input, expected):
    got = set()
    try:
        user = accounts.tests.factories.UserFactory.build(
            username=test_input)
        user.clean_fields()
    except django.core.exceptions.ValidationError as err:
        for suberr in err.error_dict['username']:
            got.add(suberr.code)
    assert got == set(expected)
