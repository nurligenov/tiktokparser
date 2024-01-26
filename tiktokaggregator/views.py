# myapp/views.py
import logging
import time

from rest_framework.response import Response
from rest_framework.views import APIView

from tiktokparser.celery import app
from .models import MusicPost, Profile
from .serializers import TikTokScrapperInputSerializer
from .tasks import process_tiktok_data, download_and_archive_videos
from celery.result import AsyncResult

logger = logging.getLogger(__name__)


class TriggerTikTokScrapper(APIView):
    queryset = MusicPost.objects.none()

    def post(self, request, *args, **kwargs):
        serializer = TikTokScrapperInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Trigger the Celery task
        res = process_tiktok_data.delay(validated_data)
        async_res = AsyncResult(res.id, app=app)
        while True:
            if async_res.state == "SUCCESS":
                logger.info("Starting download_and_archive_videos")
                profile = Profile.objects.get(url=validated_data["profiles"][0])
                download_and_archive_videos(profile)
                logger.info("Finished download_and_archive_videos")
                return Response({"status": "Scraping task finished"})
            if async_res.state == "FAILED":
                logger.error("Failed to parse posts")
                return Response({"status": "Scraping task had some errors, check admin page"})
            time.sleep(10)
