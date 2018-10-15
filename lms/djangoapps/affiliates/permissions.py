import abc
import logging

from django.shortcuts import redirect

from affiliates.models import AffiliateMembership

LOG = logging.getLogger(__name__)


class BasePermission(object):
    @abc.abstractmethod
    def has_permission(self, affiliate_slug=None):
        raise NotImplementedError()

    def dispatch(self, request, *args, **kwargs):
        affiliate_slug = kwargs.get('affiliate_slug')
        if not self.has_permission(affiliate_slug=affiliate_slug):
            LOG.info('Unauthorized attempt to access site admin by %s', self.request.user.username)
            return redirect('root')
        return super(BasePermission, self).dispatch(request, *args, **kwargs)


class IsStaffMixin(BasePermission):
    def has_permission(self, affiliate_slug=None):
        return self.request.user.is_staff


class IsGlobalStaffOrAffiliateStaff(BasePermission):
    def has_permission(self, affiliate_slug=None):
        user = self.request.user

        if user.is_staff:
            return True

        if user.is_anonymous():
            return False

        if affiliate_slug:
            return AffiliateMembership.objects.filter(
                member=user, role__in=AffiliateMembership.STAFF_ROLES, affiliate__slug=affiliate_slug
            ).exists()

        return AffiliateMembership.objects.filter(
            member=user, role__in=AffiliateMembership.STAFF_ROLES
        ).exists()
