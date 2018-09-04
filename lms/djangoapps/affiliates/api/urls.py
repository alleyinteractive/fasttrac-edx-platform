""" Affiliate API URLs. """
from django.conf.urls import patterns, url

from affiliates.api.views import DataExportView, ImpersonateView


urlpatterns = patterns(
    '',
    url(r'^impersonate$', ImpersonateView.as_view(), name='impersonate'),
    url(r'^data-exports$', DataExportView.as_view(), name='data-exports')
)
