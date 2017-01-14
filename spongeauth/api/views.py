import functools

from django.shortcuts import get_object_or_404, reverse
import django.core.exceptions
import django.http
import django.views.decorators.csrf
from django.utils import timezone

import accounts.models
import api.models


def _require_api_key(fn):
    @functools.wraps(fn)
    def _wrap(request, *args, **kwargs):
        api_key = None
        api_key = request.POST.get('api-key', request.GET.get('apiKey', None))
        if (
                not api_key or
                not api.models.APIKey.objects.filter(key=api_key).exists()):
            raise django.core.exceptions.PermissionDenied('No such API key')

        return fn(request, *args, **kwargs)

    return _wrap


def _encode_user(request, user):
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'avatar_url': request.build_absolute_uri(
            user.avatar.get_absolute_url()),
    }


def _four_oh_five(allowed):
    def _handler(request, *args, **kwargs):
        allowed_methods = ', '.join(allowed)
        resp = django.http.HttpResponse(
            'Request method not allowed. Use one of {}.'.format(allowed),
            status=405,
            content_type='text/plain')
        resp['Allow'] = allowed_methods
        return resp
    return _handler


@_require_api_key
@django.views.decorators.csrf.csrf_exempt
def list_users(request):
    handlers = {
        'POST': _create_user,
        'DELETE': _delete_user}
    handler = handlers.get(request.method, _four_oh_five(handlers.keys()))
    return handler(request)


def _create_user(request):
    username = request.POST.get('username')
    password = request.POST.get('password')
    email = request.POST.get('email')
    verified = request.POST.get('verified', 'false') == 'true'

    # There's also a dummy boolean, which is unused here.

    user = accounts.models.User(
        username=username,
        email=email,
        email_verified=verified)
    user.set_password(password)
    try:
        user.save()
    except django.db.IntegrityError as exc:
        return django.http.JsonResponse({
            'error': str(exc)}, status=422)
    resp = django.http.JsonResponse(
        _encode_user(request, user), status=201)
    resp['Location'] = reverse('api:users-detail', kwargs={'username': user.username})
    return resp


def _delete_user(request):
    username = request.GET.get('username')

    user = get_object_or_404(accounts.models.User, is_active=True, username=username)
    user.is_active = False
    user.deleted_at = timezone.now()
    user.save()
    return django.http.JsonResponse(
        _encode_user(request, user), status=200)


@_require_api_key
def user_detail(request, username):
    handlers = {
        'GET': _user_detail}
    handler = handlers.get(request.method, _four_oh_five(handlers.keys()))
    return handler(request, username)


def _user_detail(request, username):
    user = get_object_or_404(accounts.models.User, is_active=True, username=username)
    return django.http.JsonResponse(
        _encode_user(request, user),
        status=200)
