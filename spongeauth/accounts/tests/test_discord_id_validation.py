import django.core.exceptions

import pytest

import accounts.models
import accounts.tests.factories


BAD_EXAMPLES = [
    ("felixoi#3123", []),
    ("testaccountxyz#9872", []),
    ("foobar#12345", ['wrong_pattern']),
    ("ewoutvs_", ['wrong_pattern']),
    ("#1234", ['wrong_pattern']),
]


@pytest.mark.parametrize("test_input,expected", BAD_EXAMPLES)
def test_validate_username(test_input, expected):
    got = set()
    try:
        accounts.models.validate_discord_id(test_input)
    except django.core.exceptions.ValidationError as err:
        for suberr in err.error_list:
            got.add(suberr.code)
    assert got == set(expected)


@pytest.mark.parametrize("test_input,expected", BAD_EXAMPLES)
def test_validate_username_model(test_input, expected):
    got = set()
    try:
        user = accounts.tests.factories.UserFactory.build(
            discord_id=test_input)
        user.clean_fields()
    except django.core.exceptions.ValidationError as err:
        for suberr in err.error_dict['discord_id']:
            got.add(suberr.code)
    assert got == set(expected)
