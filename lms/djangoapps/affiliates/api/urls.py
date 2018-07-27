""" Affiliate API URLs. """
from django.conf.urls import patterns, url

from affiliates.api.views import ImpersonateView


urlpatterns = patterns(
    '',
    url(r'^impersonate$', ImpersonateView.as_view(), name='impersonate')
)
