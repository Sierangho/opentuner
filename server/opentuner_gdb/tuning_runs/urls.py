from django.conf.urls import patterns, url

from tuning_runs import views

urlpatterns = patterns('',
	url(r'^$', views.index, name='index'),
	url(r'^view_pearson/(\w+)/$', views.view_pearson, {'spearman':False, 'lookup':True}),
	url(r'^view_spearman/(\w+)/$', views.view_pearson, {'spearman':True, 'lookup':True}),
	url(r'^view_normalized/(\w+)/$', views.view_normalized),
	url(r'^view_grouped/(\w+)/$', views.view_grouped),
	url(r'^view_ranks/(\w+)/$', views.view_ranks),

	url(r'^view_pearson_expanded/(\w+)/$', views.view_pearson, {'spearman':False, 'lookup':False}),
	url(r'^view_spearman_expanded/(\w+)/$', views.view_pearson, {'spearman':True, 'lookup':False}),
	url(r'^view_normalized_expanded/(\w+)/$', views.view_normalized, {'lookup':False}),
	url(r'^view_grouped_expanded/(\w+)/$', views.view_grouped, {'lookup':False}),

	url(r'^view_correlations/(\w+)/$', views.view_all),



	url(r'^update_ranks/(\w+)/$', views.update_ranks),
	#url(r'^update_ranks/$', views.update_all_ranks),
	url(r'^get_similar/(\w+)/$', views.get_similar),
	url(r'^see_distances/(\w+)/$', views.see_distances),
	url(r'^upload/$',views.upload),
)