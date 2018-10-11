from functools import wraps

from django.http import HttpResponseForbidden

from .models import AffiliateMembership


def only_program_director(function):
    """Only allow access to global staff or the affiliate's Program Director."""
    @wraps(function)
    def wrapped_view(request, *args, **kwargs):
        """Wrapper for the view function."""
        if request.user.is_anonymous():
            return HttpResponseForbidden()

        if request.user.is_staff:
            return function(request, *args, **kwargs)

        if 'slug' in kwargs:
            has_pd_role_in_affiliate = AffiliateMembership.objects.filter(
                member=request.user,
                affiliate__slug=kwargs['slug'],
                role=AffiliateMembership.STAFF
            ).exists()

            if has_pd_role_in_affiliate:
                return function(request, *args, **kwargs)
        return HttpResponseForbidden()

    return wrapped_view


def only_staff(function):
    """Only allow access to global staff or affiliate staff (Program Director or Course Manager)."""
    @wraps(function)
    def wrapped_view(request, *args, **kwargs):
        """Wrapper for the view function."""
        if request.user.is_anonymous():
            return HttpResponseForbidden()

        if request.user.is_staff:
            return function(request, *args, **kwargs)

        if 'slug' in kwargs:
            has_pd_or_cm_role_in_affiliate = AffiliateMembership.objects.filter(
                role__in=AffiliateMembership.STAFF_ROLES,
                member=request.user,
                affiliate__slug=kwargs['slug']
            ).exists()

            if has_pd_or_cm_role_in_affiliate:
                return function(request, *args, **kwargs)
        return HttpResponseForbidden()

    return wrapped_view
