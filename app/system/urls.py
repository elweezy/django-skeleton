from django.conf.urls import patterns, url, include

info_urlpatterns = patterns('system.info',
    url(r'^request/$', 'request_info', name='system_info_request'),
    url(r'^localization/$', 'localization_info', name='system_info_localization'),
)

urlpatterns = patterns('system.views',
    # Error pages
    url(r'^error/400/$', 'error_400', name='error_400'),
    url(r'^error/403/$', 'error_403', name='error_403'),
    url(r'^error/404/$', 'error_404', name='error_404'),
    url(r'^error/500/$', 'error_500', name='error_500'),
    # System info pages
    url(r'^info/', include(info_urlpatterns)),
)
