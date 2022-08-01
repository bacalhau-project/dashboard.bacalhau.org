from django.urls import path, include

from django.contrib import admin

admin.autodiscover()

import dashboards.views

# To add a new path, first import the app:
urlpatterns = [
    path("", dashboards.views.index, name="index"),
    path("rawstats", dashboards.views.rawStats, name="rawstats"),
    path("admin/", admin.site.urls),
]
