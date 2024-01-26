from django.contrib import admin

from .models import MusicPost, VideoPost


@admin.register(MusicPost)
class MusicPostAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "status", "music_url", "created_at", "updated_at")
    list_filter = ("status", "created_at", "updated_at")
    search_fields = ("author", "status")
    readonly_fields = ("id", "created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        # Make all fields read-only if the post status is 'finished'
        if obj and obj.status == "finished":
            return [f.name for f in self.model._meta.fields]
        return self.readonly_fields


@admin.register(VideoPost)
class VideoPostAdmin(admin.ModelAdmin):
    list_display = ("id", "retrieved_from_post", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("retrieved_from_post__author",)
    readonly_fields = ("id", "created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields
