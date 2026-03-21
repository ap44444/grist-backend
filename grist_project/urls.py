from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from core import views as core_views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from core.views import AppointmentViewSet

router = DefaultRouter()
router.register(r'appointments', AppointmentViewSet, basename='appointment')

urlpatterns = [
    path("admin/", admin.site.urls),
    path('health/', core_views.health_check),

    #notification
    path('api/dietitian/notifications/', core_views.get_system_notifications_view, name='system_notifications'),

    # Autentication
    path('api/register/', core_views.RegisterView.as_view(), name='register'),
    path('api/login/', TokenObtainPairView.as_view(), name='login'),
    path('api/logout/', core_views.logout_user, name='logout'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/google/', core_views.GoogleLogin.as_view(), name='google_login'),
    # Dashboard and stats
    path('api/dashboard/today/', core_views.get_dashboard_data, name='dashboard_today'),
    path('api/stats/progress/', core_views.get_progress_stats, name='progress_stats'),
    path('api/dietitian/dashboard/today/', core_views.get_dietitian_dashboard, name='dietitian_dashboard'),
    path('api/dietitian/appointments/', core_views.get_dietitian_appointments, name='dietitian_appointments_list'),
    path('api/dietitian/dashboard/today/', core_views.get_dietitian_dashboard, name='dietitian_dashboard'),
    path('api/dietitian/appointments/', core_views.get_dietitian_appointments, name='dietitian_appointments_list'),

    # Profile and goals
    path('api/profile/', core_views.get_profile_data, name='get_profile_data'),
    path('api/profile/update/', core_views.update_profile, name='update_profile'),
    path('api/profile/calculate-targets/', core_views.calculate_and_save_calories, name='calculate_targets'),
    path('api/profile/manage/', core_views.UserProfileCRUDView.as_view(), name='manage-profile'),
    path('api/dietitian/profile/', core_views.get_dietitian_profile_view, name='dietitian_profile'),
    # Daily tracking
    path('api/track/water/', core_views.track_water, name='track_water'),
    path('api/track/meal/<int:meal_slot_id>/', core_views.track_meal, name='track_meal'),

    # Recipies and meal plans
    path('api/recipe/request/', core_views.request_recipe, name='request_recipe'),
    path('api/meals/<int:meal_slot_id>/substitute/', core_views.request_substitution, name='substitute_ingredient'),

    # Grocery cart
    path('api/cart/', core_views.get_grocery_cart, name='get_cart'),
    path('api/cart/add/', core_views.add_cart_item, name='add_cart_item'),
    path('api/cart/item/<int:item_id>/update/', core_views.update_cart_item, name='update_item'),
    path('api/cart/item/<int:item_id>/delete/', core_views.delete_cart_item, name='delete_item'),

    # API Documentation (Swagger)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

                  # Dietitian ratings and reviews
    path('api/dietitians/<int:dietitian_id>/reviews/', core_views.get_dietitian_reviews,name='get_reviews'),
    path('api/patient/reviews/submit/', core_views.submit_review_view, name='submit_review_view'),

    #profile picture
    path('api/profile/upload-picture/', core_views.upload_profile_picture, name='upload_picture'),


    path('api/dietitian/clients/', core_views.get_active_clients_view, name='active_clients_list'),

    path('api/patient/reviews/submit/', core_views.submit_review_view, name='submit_review'),
]+ router.urls
