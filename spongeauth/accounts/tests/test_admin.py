import unittest.mock

from .. import admin
from .. import models
from . import factories


class TestAdminUserChangeForm:
    def test_clean_password(self):
        user = factories.UserFactory.build()
        form = admin.AdminUserChangeForm(instance=user)
        assert form.clean_password() == user.password


class TestUserAdmin:
    def test_get_readonly_fields(self):
        admin_user = factories.UserFactory.build(is_admin=True, is_staff=True)
        staff_user = factories.UserFactory.build(is_staff=True)
        user = factories.UserFactory.build()

        request = unittest.mock.MagicMock()
        obj = admin.UserAdmin(models.User, None)

        request.user = admin_user
        assert obj.get_readonly_fields(request, admin_user) == ()
        assert obj.get_readonly_fields(request, staff_user) == ()
        assert obj.get_readonly_fields(request, user) == ()

        request.user = staff_user
        assert 'username' in obj.get_readonly_fields(request, admin_user)
        assert 'username' not in obj.get_readonly_fields(request, staff_user)
        assert 'is_staff' in obj.get_readonly_fields(request, staff_user)
        assert 'is_admin' in obj.get_readonly_fields(request, staff_user)
        assert 'is_staff' in obj.get_readonly_fields(request, user)
        assert 'is_admin' in obj.get_readonly_fields(request, user)

    def test_delete_model(self):
        user = factories.UserFactory.build()
        assert user.deleted_at is None
        assert user.is_active
        user.save = lambda: None

        obj = admin.UserAdmin(models.User, None)
        obj.delete_model(None, user)
        assert user.deleted_at is not None
        assert not user.is_active
