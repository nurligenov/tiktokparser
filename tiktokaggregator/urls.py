from django.urls import path

from .views import TriggerTikTokScrapper

urlpatterns = [
    path(
        "trigger-tiktok-scrapper/",
        TriggerTikTokScrapper.as_view(),
        name="trigger-tiktok-scrapper",
    ),
]
