from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.http import urlencode


@login_required
def index(request):
    return render(request, 'core/index.html')


def admin_login_redirect(request):
    if request.user.is_authenticated and not request.user.is_staff:
        return redirect('index')

    return redirect('{}?{}'.format(
        reverse('accounts:login'),
        urlencode({'next': request.GET.get('next', '/')})))
