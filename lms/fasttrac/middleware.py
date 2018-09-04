from django.conf import settings

from lms.fasttrac.slack import send_slack_notification


class FTSlackErrorMiddleware(object):
    """Intercepts an error and send the error message with additional information to slack."""
    def process_exception(self, request, exception):
        if settings.SLACK_WEBHOOK_URL:
            send_slack_notification(request, str(exception))
        return None
