from django.contrib import messages
import logging
from django.contrib import admin

from .models import MusicPost, VideoPost, download_and_archive_videos

logger = logging.getLogger(__name__)


@admin.register(MusicPost)
class MusicPostAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "status", "music_url", "created_at", "updated_at")
    list_filter = ("status", "created_at", "updated_at")
    search_fields = ("author", "status")
    readonly_fields = ("id", "created_at", "updated_at")
    actions = ['archive_videos']

    def get_readonly_fields(self, request, obj=None):
        # Make all fields read-only if the post status is 'finished'
        if obj and obj.status == "finished":
            return [f.name for f in self.model._meta.fields]
        return self.readonly_fields

    def archive_videos(self, request, queryset):
        logger.info(queryset)
        try:
            download_and_archive_videos(queryset[0])
            self.message_user(request, f"Successfully archived videos for {queryset[0]}", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Error archiving videos for {queryset[0]}: {e}", messages.ERROR)

    archive_videos.short_description = "Download and Archive Videos for selected MusicPosts"


@admin.register(VideoPost)
class VideoPostAdmin(admin.ModelAdmin):
    list_display = ("id", "retrieved_from_post", "download_video_id", "download_video_url", "status", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at", "status")
    search_fields = ("retrieved_from_post__author",)
    readonly_fields = ("id", "created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields
