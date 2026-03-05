from django.contrib import admin
from django.urls import path
from core import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # The API Address for kotlin to send the user profile data
    path('api/profile/update/', core_views.update_profile, name='update_profile'),
    # The API Address for  Kotlin  to request a recipe
    path('api/recipe/request/', core_views.request_recipe, name='request_recipe'),
]
