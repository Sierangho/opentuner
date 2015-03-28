from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'opentuner_gdb.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^tuning_runs/', include('tuning_runs.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
