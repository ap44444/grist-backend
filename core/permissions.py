from rest_framework.permissions import BasePermission


class IsDietitian(BasePermission):
    """
    Custom security class: Only allows users with the 'DIETITIAN' role to access the endpoint.
    """

    def has_permission(self, request, view):
        # 1. First, check if they are logged in
        if not bool(request.user and request.user.is_authenticated):
            return False

        # 2. Then, check if they have a profile and if that profile's role is exactly 'DIETITIAN'
        return bool(
            hasattr(request.user, 'profile') and
            request.user.profile.role == 'DIETITIAN'
        )