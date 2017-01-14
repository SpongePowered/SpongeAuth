import django.http

import unittest.mock

from .. import middleware


def get_response(req):
    # dummy get_response, just return an empty response
    return django.http.HttpResponse()


def test_leaves_remote_addr_alone_if_no_real_ip():
    remote_addr = object()
    request = unittest.mock.MagicMock()
    request.META = {'REMOTE_ADDR': remote_addr}

    middleware.XRealIPMiddleware(get_response)(request)

    assert request.META['REMOTE_ADDR'] is remote_addr


def test_switches_out_x_real_ip_if_available():
    remote_addr = object()
    x_real_ip = object()

    request = unittest.mock.MagicMock()
    request.META = {'REMOTE_ADDR': remote_addr, 'HTTP_X_REAL_IP': x_real_ip}

    middleware.XRealIPMiddleware(get_response)(request)

    assert request.META['REMOTE_ADDR'] is x_real_ip
    assert request.META['HTTP_X_REAL_IP'] is x_real_ip
