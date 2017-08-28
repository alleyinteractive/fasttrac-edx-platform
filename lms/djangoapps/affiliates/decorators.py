from django.http import HttpResponseForbidden
from functools import wraps
from .models import AffiliateMembership, AffiliateEntity

def only_program_director(function):
    """Only allow access to global staff or affiliate staff user(Program Director)"""
    @wraps(function)
    def wrapped_view(request, *args, **kwargs):
        """Wrapper for the view function."""
        if request.user.is_anonymous():
            return HttpResponseForbidden()
        elif request.user.is_staff:
            return function(request, *args, **kwargs)
        else:
            affiliate = AffiliateEntity.objects.get(slug=kwargs['slug'])

            has_pd_role_in_affiliate = AffiliateMembership.objects.filter(member=request.user, affiliate=affiliate, role='staff').exists()

            if has_pd_role_in_affiliate:
                return function(request, *args, **kwargs)
            else:
                return HttpResponseForbidden()

    return wrapped_view


def only_staff(function):
    """Only allow access to global staff or affiliate staff user(Program Director)"""
    @wraps(function)
    def wrapped_view(request, *args, **kwargs):
        """Wrapper for the view function."""
        if request.user.is_anonymous():
            return HttpResponseForbidden()
        elif request.user.is_staff:
            return function(request, *args, **kwargs)
        else:
            affiliate = AffiliateEntity.objects.get(slug=kwargs['slug'])

            has_pd_role_in_affiliate = AffiliateMembership.objects.filter(member=request.user, affiliate=affiliate, role='staff').exists()
            has_cm_role_in_affiliate = AffiliateMembership.objects.filter(member=request.user, affiliate=affiliate, role='instructor').exists()

            if has_pd_role_in_affiliate or has_cm_role_in_affiliate:
                return function(request, *args, **kwargs)
            else:
                return HttpResponseForbidden()


    return wrapped_view
