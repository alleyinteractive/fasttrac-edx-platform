import logging

from django.conf import settings
from django.contrib.auth import login, load_backend
from django.contrib.auth.models import User
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response

LOG = logging.getLogger(__name__)


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


def _get_path_of_arbitrary_backend_for_user(user):
    """
    Return the path to the first found authentication backend that recognizes the given user.
    """
    for backend_path in settings.AUTHENTICATION_BACKENDS:
        backend = load_backend(backend_path)
        if backend.get_user(user.id):
            return backend_path
    return None
