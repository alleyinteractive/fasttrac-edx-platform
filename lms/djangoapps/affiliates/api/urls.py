""" Affiliate API URLs. """
from django.conf.urls import patterns, url

from affiliates.api.views import (
    AffiliateEntityViewSet,
    AffiliateEntityDetailsViewSet,
    AffiliateMembershipViewSet,
    AffiliateMembershipDetailsViewSet,
    AffiliateInviteDetailsViewSet,
    DataExportView,
    GetAffiliates,
    ImpersonateView
)


urlpatterns = patterns(
    '',
    url(r'^$', AffiliateEntityViewSet.as_view(), name='create'),
    url(r'^impersonate$', ImpersonateView.as_view(), name='impersonate'),
    url(r'^data-exports$', DataExportView.as_view(), name='data-exports'),
    url(r'^get-affiliates', GetAffiliates.as_view(), name='get-affiliates'),
    url(r'^(?P<affiliate_slug>[^/]+)$', AffiliateEntityDetailsViewSet.as_view(), name='details'),
    url(r'^(?P<affiliate_slug>[^/]+)/membership$', AffiliateMembershipViewSet.as_view(), name='membership'),
    url(
        r'^(?P<affiliate_slug>[^/]+)/membership/(?P<membership_id>[\d]+)$',
        AffiliateMembershipDetailsViewSet.as_view(),
        name='membership-details'
    ),
    url(
        r'^(?P<affiliate_slug>[^/]+)/membership/invite/(?P<invite_id>[\d]+)$',
        AffiliateInviteDetailsViewSet.as_view(),
        name='invite-details'
    ),
)
