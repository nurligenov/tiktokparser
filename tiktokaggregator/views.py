# myapp/views.py
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MusicPost
from .serializers import TikTokScrapperInputSerializer
from .tasks import process_tiktok_data


class TriggerTikTokScrapper(APIView):
    queryset = MusicPost.objects.none()

    def post(self, request, *args, **kwargs):
        serializer = TikTokScrapperInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Trigger the Celery task
        process_tiktok_data.delay(validated_data)

        return Response({"status": "Scraping task initiated"})
