import logging

from django.conf import settings
from django.contrib.auth import login, load_backend
from django.contrib.auth.models import User
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response

from instructor_task.models import ReportStore

from affiliates.tasks import (
    export_csv_user_report,
    export_csv_affiliate_course_report,
    export_csv_affiliate_report,
    export_csv_course_report,
    export_csv_interactives_completion_report
)


LOG = logging.getLogger(__name__)


def _get_path_of_arbitrary_backend_for_user(user):
    """
    Return the path to the first found authentication backend that recognizes the given user.
    """
    for backend_path in settings.AUTHENTICATION_BACKENDS:
        backend = load_backend(backend_path)
        if backend.get_user(user.id):
            return backend_path
    return None


class ImpersonateView(APIView):
    """
    Login as a different user.
    """
    permission_classes = (IsAdminUser,)

    def post(self, request):
        email = request.POST.get('email')

        try:
            user = User.objects.get(email=email)
            if not hasattr(request.user, 'backend'):
                user.backend = _get_path_of_arbitrary_backend_for_user(user)
            login(request, user)
            LOG.info('Impersonating %s', email)
            return Response(
                data={'msg': 'User logged in.'},
                status=200,
                content_type='application/json'
            )
        except User.DoesNotExist:
            LOG.info('Impersonation for %s failed', email)
            return Response(
                data={'msg': 'User with email {} does not exist.'.format(email)},
                status=400,
                content_type='application/json'
            )


class DataExportView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        report_store = ReportStore.from_config('GRADES_DOWNLOAD')
        return Response(
            data={'exports': report_store.links_for('affiliates')},
            status=200,
            content_type='application/json'
        )

    def post(self, request):
        report_type = request.POST.get('report_type')

        if report_type == 'export_csv_affiliate_report':
            export_csv_affiliate_report.delay()
        elif report_type == 'export_csv_affiliate_course_report':
            export_csv_affiliate_course_report.delay()
        elif report_type == 'export_csv_user_report':
            export_csv_user_report.delay()
        elif report_type == 'export_csv_time_report':
            export_csv_course_report.delay(time_report=True)
        elif report_type == 'export_csv_completion_report':
            export_csv_course_report.delay(time_report=False)
        elif report_type == 'export_completion_report':
            export_csv_interactives_completion_report.delay()

        return Response(status=200)
