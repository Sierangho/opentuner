from django.conf.urls import patterns, url

from tuning_runs import views

urlpatterns = patterns('',
	url(r'^$', views.index, name='index'),
	url(r'^update_ranks/(\w+)/$', views.update_ranks),
	url(r'^upload/$',views.upload),
)