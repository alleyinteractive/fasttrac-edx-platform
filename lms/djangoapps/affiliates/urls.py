"""
URLs for the Affiliate Feature.
"""
from django.conf.urls import patterns, url

from affiliates.views import AffiliateAdminView, ImpersonateView, SiteAdminView


urlpatterns = patterns(
    '',
    url(r'^$', 'affiliates.views.index', name='index'),
    # When no slug is provided it will be redirected to the
    # affiliate admin page of the request user's default affiliate.
    url(r'^affiliate-admin$', AffiliateAdminView.as_view(), name='affiliate-admin-redirect'),
    url(r'^affiliate-admin/(?P<affiliate_slug>[^/]*)$', AffiliateAdminView.as_view(), name='affiliate-admin'),
    url(r'^admin$', SiteAdminView.as_view(), name='admin'),
    url(r'^payment$', 'affiliates.views.payment', name='payment'),
    url(r'^new$', 'affiliates.views.new', name='new'),
    url(r'^create$', 'affiliates.views.create', name='create'),
    url(r'^impersonate', ImpersonateView.as_view(), name='impersonate'),
    url(r'^(?P<slug>[^/]*)$', 'affiliates.views.show', name='show'),
    url(r'^edit/(?P<slug>[^/]*)$', 'affiliates.views.edit', name='edit'),
    url(r'^delete/(?P<slug>[^/]*)$', 'affiliates.views.delete', name='delete'),
    url(r'^edit/(?P<slug>[^/]*)/add_member$', 'affiliates.views.add_member', name='add_member'),
    url(
        r'^edit/(?P<slug>[^/]*)/remove_member/(?P<member_id>\d+)$',
        'affiliates.views.remove_member',
        name='remove_member'
    ),
    url(
        r'^edit/(?P<slug>[^/]*)/remove_invite/(?P<invite_id>\d+)$',
        'affiliates.views.remove_invite',
        name='remove_invite'
    ),
    url(
        r'^toggle_active_status/(?P<slug>[^/]*)',
        'affiliates.views.toggle_active_status',
        name='toggle_active_status'
    ),
)
