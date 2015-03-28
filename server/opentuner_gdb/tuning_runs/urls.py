from django.conf.urls import patterns, url

from tuning_runs import views

urlpatterns = patterns('',
	url(r'^$', views.index, name='index'),
	url(r'^add_runs/(\w+)/$', views.add_runs),
	url(r'^upload/$',views.upload),
)