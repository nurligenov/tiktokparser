# serializers.py
from rest_framework import serializers


class TikTokScrapperInputSerializer(serializers.Serializer):
    disableCheerioBoost = serializers.BooleanField(default=False)
    disableEnrichAuthorStats = serializers.BooleanField(default=False)
    hashtags = serializers.ListField(
        child=serializers.CharField(max_length=100), required=False, default=[]
    )
    profiles = serializers.ListField(
        child=serializers.CharField(max_length=200), required=False, default=[]
    )
    resultsPerPage = serializers.IntegerField(default=100)
    shouldDownloadCovers = serializers.BooleanField(default=False)
    shouldDownloadSlideshowImages = serializers.BooleanField(default=False)
    shouldDownloadVideos = serializers.BooleanField(default=False)
    searchSection = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    maxProfilesPerQuery = serializers.IntegerField(default=10)
