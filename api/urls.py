from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'request', views.RequestViewSet, basename='request')

urlpatterns = [
    path('', include(router.urls)),
]
