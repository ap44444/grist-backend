from django.contrib import admin
from django.urls import path
from core import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # The API Address
    path('api/profile/update/', core_views.update_profile, name='update_profile'),
]