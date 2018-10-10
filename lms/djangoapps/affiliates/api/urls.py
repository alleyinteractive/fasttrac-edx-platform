""" Affiliate API URLs. """
from django.conf.urls import patterns, url

from affiliates.api.views import (
    AffiliateEntityViewSet,
    AffiliateEntityDetailsViewSet,
    AffiliateEntityMembershipViewSet,
    AffiliateEntityFacilitators,
    DataExportView,
    ImpersonateView
)


urlpatterns = patterns(
    '',
    url(r'^$', AffiliateEntityViewSet.as_view(), name='create'),
    url(r'^impersonate$', ImpersonateView.as_view(), name='impersonate'),
    url(r'^data-exports$', DataExportView.as_view(), name='data-exports'),
    url(r'^check-membership', AffiliateEntityFacilitators.as_view(), name='check-membership'),
    url(r'^(?P<affiliate_slug>[^/]+)$', AffiliateEntityDetailsViewSet.as_view(), name='details'),
    url(r'^(?P<affiliate_slug>[^/]+)/membership$', AffiliateEntityMembershipViewSet.as_view(), name='membership'),
)
