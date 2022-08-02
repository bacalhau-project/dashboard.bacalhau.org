from django.urls import path, include

from django.contrib import admin

admin.autodiscover()

import dashboards.views

# To add a new path, first import the app:
urlpatterns = [
    path("", dashboards.views.index, name="index"),
    path("rawstats.json", dashboards.views.rawStats, name="rawstats.json"),
    path("grafanaperfstats.json", dashboards.views.grafanaPerfStats, name="grafanaperfstats.json"),
    path("admin/", admin.site.urls),
]
