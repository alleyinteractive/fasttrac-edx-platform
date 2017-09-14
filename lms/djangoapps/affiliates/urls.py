"""
URLs for the Affiliate Feature.
"""
from django.conf.urls import patterns, url


urlpatterns = patterns('',
    url(r'^$', 'affiliates.views.index', name='index'),
    url(r'^admin$', 'affiliates.views.admin', name='admin'),
    url(r'^payment$', 'affiliates.views.payment', name='payment'),
    url(r'^new$', 'affiliates.views.new', name='new'),
    url(r'^create$', 'affiliates.views.create', name='create'),
    url(r'^(?P<slug>[^/]*)$', 'affiliates.views.show', name='show'),
    url(r'^edit/(?P<slug>[^/]*)$', 'affiliates.views.edit', name='edit'),
    url(r'^delete/(?P<slug>[^/]*)$', 'affiliates.views.delete', name='delete'),
    url(r'^edit/(?P<slug>[^/]*)/add_member$', 'affiliates.views.add_member', name='add_member'),
    url(r'^edit/(?P<slug>[^/]*)/remove_member/(?P<member_id>\d+)$', 'affiliates.views.remove_member', name='remove_member'),
)
