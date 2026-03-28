from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from .views import MeView, RegisterView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='user-register'),
    path('me/', MeView.as_view(), name='user-me'),
    path('token/', obtain_auth_token, name='user-token'),
]
