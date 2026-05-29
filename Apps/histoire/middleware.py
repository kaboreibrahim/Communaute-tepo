from Apps.histoire.services import log_request_action, should_log_request


class ActionHistoryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if should_log_request(request):
            try:
                log_request_action(request, response)
            except Exception:
                pass

        return response
