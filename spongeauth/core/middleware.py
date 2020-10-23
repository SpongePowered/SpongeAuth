class XRealIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.META.get("X-Forwarded-For", ",").split(",")[0]:
            request.META["REMOTE_ADDR"] = request.META["HTTP_X_REAL_IP"]

        response = self.get_response(request)
        return response
