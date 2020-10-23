class XRealIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        real_ip = request.META.get("HTTP_X_FORWARDED_FOR", ",").split(",")[0]
        if real_ip and real_ip != request.META["REMOTE_ADDR"]:
            request.META["REMOTE_ADDR"] = real_ip

        response = self.get_response(request)
        return response
