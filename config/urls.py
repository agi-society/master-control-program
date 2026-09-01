from django.contrib import admin
from django.urls import path, include
from work import views
urlpatterns = [
    path('setup/', views.setup_admin, name='setup_admin'),
    path('admin/', admin.site.urls),
    path('', include('work.urls')),
    path('', include('django.contrib.auth.urls')),
]
