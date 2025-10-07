from rest_framework import generics
from .models import Profile
from .serializers import ProfileSerializer

class RegisterView(generics.CreateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
