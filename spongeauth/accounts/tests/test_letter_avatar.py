from .. import letter_avatar

import pytest


@pytest.mark.parametrize(
    "username,expected", [("lukegb", "e47774"), ("windy", "91b2a8"), ("Moose", "ee7513"), ("sAlaMi", "f05b48")]
)
def test_colours(username, expected):
    assert letter_avatar.LetterAvatar(username).colour == expected


def test_get_absolute_url():
    av = letter_avatar.LetterAvatar("sAlaMi")
    assert av.get_absolute_url() == (
        "https://forums-cdn.spongepowered.org/letter_avatar_proxy/" "v2/letter/s/f05b48/240.png"
    )
