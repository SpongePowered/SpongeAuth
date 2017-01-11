import django.test
import django.shortcuts
import django.http

from . import factories


class TestLogoutSuccess(django.test.TestCase):
    def path(self):
        return django.shortcuts.reverse('accounts:logout-success')

    def test_redirects_to_index_if_logged_in(self):
        user = factories.UserFactory.create()
        client = django.test.Client()
        client.login(username=user.username, password='secret')

        resp = client.get(self.path())
        assert resp.status_code == 302
        assert resp['Location'] == django.shortcuts.reverse('index')

    def test_renders_logged_out_page(self):
        client = django.test.Client()
        with self.assertTemplateUsed('accounts/logout_success.html'):
            resp = client.get(self.path())
        assert resp.status_code == 200


class TestLogout(django.test.TestCase):
    def setUp(self):
        self.user = factories.UserFactory.create()
        self.client = django.test.Client()
        self.login(self.client, self.user)

    def login(self, c, user):
        assert c.login(username=user.username, password='secret')

    def path(self):
        return django.shortcuts.reverse('accounts:logout')

    def test_redirects_to_index_if_logged_out(self):
        client = django.test.Client()
        resp = client.get(self.path())
        assert resp.status_code == 302
        assert resp['Location'] == django.shortcuts.reverse('index')

    def test_renders_form_on_get(self):
        with self.assertTemplateUsed('accounts/logout.html'):
            resp = self.client.get(self.path())
        assert resp.status_code == 200

    def test_logs_out_on_post(self):
        resp = self.client.post(self.path())
        self.assertRedirects(resp, django.shortcuts.reverse('accounts:logout-success'))
        assert resp.status_code == 302
        user = django.contrib.auth.get_user(self.client)
        assert not user.is_authenticated()


class TestAvatarForUser(django.test.TestCase):
    def setUp(self):
        self.user = factories.UserFactory.create()

    def path(self, username):
        return django.shortcuts.reverse('avatar-for-user',
                                        kwargs={'username': username})

    def test_404_on_not_exist(self):
        resp = self.client.get(self.path(self.user.username + 'b'))
        assert resp.status_code == 404

    def test_redirects(self):
        resp = self.client.get(self.path(self.user.username))
        assert resp.status_code == 302
        assert resp['Location'] == self.user.avatar.get_absolute_url()
