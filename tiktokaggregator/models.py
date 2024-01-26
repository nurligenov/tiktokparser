import uuid

from django.db import models
from django.utils import timezone


class BasePostModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class MusicPost(BasePostModel):
    STATUS_CREATED = "created"
    STATUS_PENDING = "pending"
    STATUS_FAILED = "failed"
    STATUS_FINISHED = "finished"
    STATUS_CHOICES = [
        (STATUS_CREATED, STATUS_CREATED),
        (STATUS_PENDING, STATUS_PENDING),
        (STATUS_FAILED, STATUS_FAILED),
        (STATUS_FINISHED, STATUS_FINISHED),
    ]
    author = models.CharField(max_length=255, db_index=True)
    text = models.TextField()
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, db_index=True, default=STATUS_CREATED
    )
    music_url = models.URLField(max_length=500, unique=True, db_index=True)
    profile = models.CharField(max_length=255, null=True)

    def __str__(self):
        return f"Post {self.id} by {self.author}"


class VideoPost(BasePostModel):
    retrieved_from_post = models.ForeignKey(MusicPost, on_delete=models.PROTECT)
    video = models.FileField(upload_to="videos/")
    download_video_id = models.CharField(max_length=256, db_index=True, unique=True)

    def __str__(self):
        return f"VideoPost related to Post {self.retrieved_from_post.id} by {self.retrieved_from_post.author}"
