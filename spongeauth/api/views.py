import functools
import http

from django.shortcuts import get_object_or_404, reverse
import django.core.exceptions
import django.http
import django.views.decorators.csrf
from django.utils import timezone
from django.core.exceptions import ValidationError

from accounts.views import change_other_avatar_key as base_change_other_avatar_key

import accounts.models
import api.models


def _require_api_key(fn):
    @functools.wraps(fn)
    def _wrap(request, *args, **kwargs):
        api_key = None
        api_key = request.POST.get("api-key", request.GET.get("apiKey", None))
        if not api_key or not api.models.APIKey.objects.filter(key=api_key).exists():
            raise django.core.exceptions.PermissionDenied("No such API key")

        return fn(request, *args, **kwargs)

    return _wrap


def _encode_group(request, group):
    return {"id": group.id, "name": group.name}


def _encode_user(request, user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "avatar_url": request.build_absolute_uri(user.avatar.get_absolute_url()),
        "groups": [_encode_group(request, group) for group in user.groups.all()],
    }


def _four_oh_five(allowed):
    def _handler(request, *args, **kwargs):
        allowed_methods = ", ".join(allowed)
        resp = django.http.HttpResponse(
            "Request method not allowed. Use one of {}.".format(allowed),
            status=http.HTTPStatus.METHOD_NOT_ALLOWED,
            content_type="text/plain",
        )
        resp["Allow"] = allowed_methods
        return resp

    return _handler


@_require_api_key
@django.views.decorators.csrf.csrf_exempt
def list_users(request):
    handlers = {"POST": _create_user, "DELETE": _delete_user}
    handler = handlers.get(request.method, _four_oh_five(handlers.keys()))
    return handler(request)


def _create_user(request):
    username = request.POST.get("username")
    password = request.POST.get("password")
    email = request.POST.get("email")
    verified = request.POST.get("verified", "false") == "true"
    dummy = request.POST.get("dummy", "false") == "true"

    user = accounts.models.User(username=username, email=email, email_verified=verified)
    user.set_password(password)

    try:
        user.full_clean()
    except ValidationError as exc:
        return django.http.JsonResponse({"error": exc.messages}, status=http.HTTPStatus.UNPROCESSABLE_ENTITY)

    try:
        user.save()
        if dummy:
            user.groups.set([accounts.models.Group.objects.get(name="Dummy")])
    except django.db.IntegrityError as exc:
        return django.http.JsonResponse({"error": [str(exc)]}, status=http.HTTPStatus.UNPROCESSABLE_ENTITY)
    resp = django.http.JsonResponse(_encode_user(request, user), status=http.HTTPStatus.CREATED)
    resp["Location"] = reverse("api:users-detail", kwargs={"username": user.username})
    return resp


def _delete_user(request):
    username = request.GET.get("username")

    user = get_object_or_404(accounts.models.User, is_active=True, username=username)
    user.is_active = False
    user.deleted_at = timezone.now()
    user.save()
    return django.http.JsonResponse(_encode_user(request, user), status=http.HTTPStatus.OK)


@_require_api_key
def user_detail(request, username):
    handlers = {"GET": _user_detail}
    handler = handlers.get(request.method, _four_oh_five(handlers.keys()))
    return handler(request, username)


def _user_detail(request, username):
    qs = accounts.models.User.objects.all().prefetch_related("groups")
    user = get_object_or_404(qs, is_active=True, username=username)
    return django.http.JsonResponse(_encode_user(request, user), status=http.HTTPStatus.OK)


change_other_avatar_key = _require_api_key(base_change_other_avatar_key)
