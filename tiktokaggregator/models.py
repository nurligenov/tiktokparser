import logging
import uuid

from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


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


class Profile(BasePostModel):
    url = models.CharField(max_length=255, db_index=True, null=True)
    video_archive = models.FileField(upload_to="videos/", null=True, blank=True)

    def __str__(self):
        return self.url

    @property
    def profile_name(self):
        return self.url.split("/")[-1]


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
    profile_url = models.ForeignKey(Profile, on_delete=models.PROTECT, null=True)

    def __str__(self):
        return f"Post {self.id} by {self.author}"


class VideoPost(BasePostModel):
    STATUS_CREATED = "created"
    STATUS_UPLOADED = "uploadedToS3"
    STATUS_CHOICES = [
        (STATUS_CREATED, STATUS_CREATED),
        (STATUS_UPLOADED, STATUS_UPLOADED),
    ]
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, db_index=True, default=STATUS_CREATED
    )
    retrieved_from_post = models.ForeignKey(MusicPost, on_delete=models.PROTECT)
    download_video_id = models.CharField(max_length=256, db_index=True, unique=True)
    download_video_url = models.CharField(max_length=500, null=True)

    def __str__(self):
        return f"VideoPost related to Post {self.retrieved_from_post.id} by {self.retrieved_from_post.author}"
