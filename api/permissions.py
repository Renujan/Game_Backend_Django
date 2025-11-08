from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit objects.
    """

    def has_permission(self, request, view):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # Write permissions are only allowed to admins
        return request.user and request.user.is_authenticated and request.user.role == 'admin'

class IsAdmin(permissions.BasePermission):
    """
    Custom permission to only allow access to admin users.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'
