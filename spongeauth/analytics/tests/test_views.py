import django.test


def test_view():
    client = django.test.Client()
    resp = client.get('/analytics/', follow=False)
    assert resp.status_code == 200
