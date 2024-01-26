import uuid
import requests
import logging
from io import BytesIO
from zipfile import ZipFile
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone

from tiktokparser.utils.helpers import ThreadWithReturnValue

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
    video_archive = models.FileField(upload_to="videos/", null=True, blank=True)

    def __str__(self):
        return f"Post {self.id} by {self.author}"


class VideoPost(BasePostModel):
    STATUS_CREATED = "created"
    STATUS_UPLOADED = "uploadedToS3"
    STATUS_CHOICES = [
        (STATUS_CREATED, STATUS_CREATED),
        (STATUS_UPLOADED, STATUS_UPLOADED)
    ]
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, db_index=True, default=STATUS_CREATED
    )
    retrieved_from_post = models.ForeignKey(MusicPost, on_delete=models.PROTECT)
    download_video_id = models.CharField(max_length=256, db_index=True, unique=True)
    download_video_url = models.CharField(max_length=500, null=True)

    def __str__(self):
        return f"VideoPost related to Post {self.retrieved_from_post.id} by {self.retrieved_from_post.author}"

    def download_video(self):
        if not self.download_video_url:
            logger.info(f"download_video_url is none or video is not None, {self.pk}")
        logger.info(f"Starting download of the video, {self.download_video_url}")

        response = requests.get(self.download_video_url, stream=True)

        if response.status_code == 200:
            logger.info(f"Starting download of the video, response: 200, {self.download_video_url}")
            video_file_name = (
                f"{self.retrieved_from_post.profile.split('/')[-1]}/{self.download_video_id}.mp4"
            )

            video_file = ContentFile(response.content)

            logger.info(f"Successfully downloaded video {self.download_video_url}")
            return video_file_name, video_file
        else:
            logger.error(f"Response error,  url: {self.download_video_url}")


def download_and_archive_videos(music_post):
    logger.info(f"Started archiving videos for profile {music_post.profile}")
    video_posts = VideoPost.objects.filter(retrieved_from_post__profile=music_post.profile, status=VideoPost.STATUS_CREATED)

    # Create a BytesIO object to store the zip archive in memory
    in_memory_zip = BytesIO()
    threads = []
    for video_post in video_posts:
        thread = ThreadWithReturnValue(target=video_post.download_video)
        thread.start()
        threads.append(thread)

    with ZipFile(in_memory_zip, 'w') as zipf:
        for thread in threads:
            result = thread.join()
            if result:
                video_file_name, video_file = result
                # Add the video file to the ZIP file
                zipf.writestr(video_file_name, video_file.read())

    # Position the cursor at the start of the BytesIO object
    in_memory_zip.seek(0)

    # Save the zip archive to the video_archive field of the MusicPost
    archive_name = f"{music_post.profile.split('/')[-1]}.zip" if music_post.profile else "archive.zip"
    music_post.video_archive.save(archive_name, ContentFile(in_memory_zip.getvalue()))

    # Close the BytesIO object
    in_memory_zip.close()

    logger.info(f"Successfully archived videos for music post {music_post.id}")
    video_posts.update(status=VideoPost.STATUS_UPLOADED)
