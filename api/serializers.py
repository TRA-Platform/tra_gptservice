# serializers.py
from django.conf import settings
from rest_framework import serializers
from .models import ApiKey, Request


class RequestSerializer(serializers.ModelSerializer):
    key = serializers.CharField(write_only=True)

    class Meta:
        model = Request
        fields = '__all__'

    def validate_key(self, value):
        try:
            api_key = ApiKey.objects.get(key=value)
            if not api_key.active:
                raise serializers.ValidationError("API key is not active")
        except ApiKey.DoesNotExist:
            raise serializers.ValidationError("API key does not exist")
        return api_key


class RequestViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = '__all__'
