import abc
import logging

from django.shortcuts import redirect

from affiliates.models import AffiliateMembership

LOG = logging.getLogger(__name__)


class BasePermission(object):
    @abc.abstractmethod
    def has_permission(self):
        raise NotImplementedError()

    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission():
            LOG.info('Unauthorized attempt to access site admin by %s', self.request.user.username)
            return redirect('root')
        return super(BasePermission, self).dispatch(request, *args, **kwargs)


class IsStaffMixin(BasePermission):
    def has_permission(self):
        return self.request.user.is_staff


class IsGlobalStaffOrAffiliateStaff(BasePermission):
    def has_permission(self):
        user = self.request.user

        if user.is_staff:
            return True

        if user.is_anonymous():
            return False

        if AffiliateMembership.objects.filter(
                member=user, role__in=AffiliateMembership.STAFF_ROLES
        ).exists():
            return True

        return False
