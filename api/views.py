# views.py
import logging

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

import api
from .models import ApiKey, Request
from .serializers import RequestSerializer
from django.conf import settings

logger = logging.getLogger(__name__)


class RequestViewSet(viewsets.ModelViewSet):
    """
    A simple ViewSet for handling requests.
    """
    queryset = Request.objects.all()
    serializer_class = RequestSerializer

    def create(self, request, **kwargs):
        serializer = RequestSerializer(data=request.data)
        if serializer.is_valid():
            api_key = serializer.validated_data.get('key')
            asynchronous = serializer.validated_data.get('asynchronous', True)
            if not api_key.active:
                return Response({'message': 'API key is not active'}, status=status.HTTP_400_BAD_REQUEST)
            is_json = serializer.validated_data.get('is_json', False)
            temperature = serializer.validated_data.get('temperature', None)
            engine = serializer.validated_data.get('engine', settings.OPENAI_ENGINE)
            max_tokens = serializer.validated_data.get('max_tokens', None)
            top_p = serializer.validated_data.get('top_p', None)
            frequency_penalty = serializer.validated_data.get('frequency_penalty', None)
            presence_penalty = serializer.validated_data.get('presence_penalty', None)

            api_key.usage += 1
            api_key.save()

            # generator = api.utils.Generator()
            # prompt = serializer.validated_data.get('request')
            # request, response = generator.ask(
            #     prompt=prompt,
            #     engine=engine,
            #     temperature=temperature,
            #     max_tokens=max_tokens,
            #     top_p=top_p,
            #     frequency_penalty=frequency_penalty,
            #     presence_penalty=presence_penalty,
            # )

            request = Request.objects.create(
                key=api_key,
                request=serializer.validated_data.get('request'),
                engine=engine,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                is_json=is_json,
                asynchronous=asynchronous,
            )
            if not asynchronous:
                try:
                    request.resolve()
                except Exception as e:
                    logger.error(f"Failed to resolve request: {e}")
                    return Response({'message': 'Failed to resolve request'},
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            serializer = RequestSerializer(request)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, **kwargs):
        request_object = self.get_object()
        request_object.cancel()
        serializer = RequestSerializer(request_object)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def resolve(self, request, **kwargs):
        request_object = self.get_object()
        request_object.resolve()
        serializer = RequestSerializer(request_object)
        return Response(serializer.data, status=status.HTTP_200_OK)
