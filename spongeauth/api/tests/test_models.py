from .. import models


def test_str():
    apikey = models.APIKey(description="blah")
    assert str(apikey) == "blah"

    apikey = models.APIKey(description="foo")
    assert str(apikey) == "foo"

    apikey = models.APIKey(description="")
    assert str(apikey) == "<unnamed API key>"
