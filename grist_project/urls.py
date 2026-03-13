from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from core import views as core_views
from rest_framework_simplejwt.views import TokenObtainPairView
from core.views import RegisterView
from django.urls import path
from core import views
urlpatterns = [
    path('api/meals/<int:meal_slot_id>/substitute/', views.request_substitution, name='substitute_ingredient'),

    path("admin/", admin.site.urls),
    # The login end point
    path('api/login/', TokenObtainPairView.as_view(), name='login'),
    # The API Address for kotlin to send the user profile data
    path('api/profile/update/', core_views.update_profile, name='update_profile'),
    # The API Address for  Kotlin  to request a recipe
    path('api/recipe/request/', core_views.request_recipe, name='request_recipe'),
    #the registration endpoint
    path('api/register/', RegisterView.as_view(), name='register'),
    # Grocery cart CRUD endpoints
    path('cart/', views.get_grocery_cart, name='get_cart'),                  # READ
    path('cart/add/', views.add_cart_item, name='add_cart_item'),            # CREATE
    path('cart/item/<int:item_id>/update/', views.update_cart_item, name='update_item'), # UPDATE
    path('cart/item/<int:item_id>/delete/', views.delete_cart_item, name='delete_item'), # DELETE
    # The Token Refresh Endpoint
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # user logout
    path('api/logout/', views.logout_user, name='logout'),
]
