import logging
import threading
from io import BytesIO
from zipfile import ZipFile

import requests
from celery import shared_task
from django.core.files.base import ContentFile
from django.db.utils import IntegrityError

from clients.apify import (TikTokScrapperClient, TikTokSoundScraperClient,
                           TikTokVideoDownloadClient)
from tiktokparser.utils.helpers import ThreadWithReturnValue

from .models import MusicPost, Profile, VideoPost

logger = logging.getLogger(__name__)


def get_existing_music_urls():
    return set(MusicPost.objects.values_list("music_url", flat=True))


def get_existing_tiktok_video_ids():
    return set(VideoPost.objects.values_list("download_video_id", flat=True))


def filter_general_posts(items, existing_urls):
    return [item for item in items if item["music_url"] not in existing_urls]


def filter_video_posts(items, existing_ids):
    return [item for item in items if item not in existing_ids]


def process_sound_tiktok_results(raw_items):
    processed_items = []
    for item in raw_items:
        # Extract relevant data from item
        text = item["text"]
        author_name = item["authorMeta"]["name"]
        tiktok_video_url = item["webVideoUrl"]

        processed_items.append(
            {
                "text": text,
                "author": author_name,
                "tiktok_video_url": tiktok_video_url,
            }
        )
    return processed_items


def process_sound_data(music_post_id, chunk_size=100):
    try:
        music_post = MusicPost.objects.get(id=music_post_id)
    except MusicPost.DoesNotExist:
        return  # MusicPost not found

    music_post.status = MusicPost.STATUS_PENDING
    music_post.save()

    client = TikTokSoundScraperClient()
    run_input = {
        "disableCheerioBoost": False,
        "disableEnrichAuthorStats": False,
        "musics": [music_post.music_url],
        "shouldDownloadCovers": False,
        "shouldDownloadSlideshowImages": False,
        "shouldDownloadVideos": False,
    }

    sound_data_generator = client.run(run_input)
    existing_tiktok_ids = get_existing_tiktok_video_ids()

    for raw_sound_data_chunk in chunked_generator(sound_data_generator, chunk_size):
        processed_chunk = process_sound_tiktok_results(raw_sound_data_chunk)

        video_download_client = TikTokVideoDownloadClient()
        download_videos = video_download_client.run(
            {
                "startUrls": [
                    {"url": item["tiktok_video_url"]} for item in processed_chunk
                ],
                "proxy": {"useApifyProxy": True},
            }
        )
        download_video_ids = [
            item["video"].split(".mp4")[0] for item in download_videos
        ]
        filtered_video_ids = filter_video_posts(download_video_ids, existing_tiktok_ids)
        video_posts = [
            VideoPost(
                retrieved_from_post=music_post,
                download_video_id=filtered_video_id,
                download_video_url=video_download_client.get_download_video_url(
                    filtered_video_id
                ),
            )
            for filtered_video_id in filtered_video_ids
        ]

        VideoPost.objects.bulk_create(video_posts, ignore_conflicts=True)
        logger.info(f"{filtered_video_ids} is saved")
    music_post.status = MusicPost.STATUS_FINISHED
    music_post.save()


@shared_task
def process_tiktok_data(run_input):
    client = TikTokScrapperClient()
    raw_items_generator = client.run(run_input)
    logger.info(run_input)
    profile, _ = Profile.objects.get_or_create(url=run_input["profiles"][0])

    # Process items from the generator
    for raw_items_chunk in chunked_generator(raw_items_generator, chunk_size=100):
        processed_items = process_tiktok_results(raw_items_chunk)
        save_posts_in_chunks(processed_items, profile)
    logger.info("Saved all posts sussesfully")
    logger.info("Starting download_and_archive_videos")
    download_and_archive_videos(profile)
    logger.info("Finished download_and_archive_videos")


def process_tiktok_results(raw_items):
    processed_items = []
    for item in raw_items:
        # Extract relevant data from item
        text = item.get("text", "")
        author_name = item.get("authorMeta", {}).get("name", "")
        music_name = item.get("musicMeta", {}).get("musicName", "")
        music_id = item.get("musicMeta", {}).get("musicId", "")
        music_url = (
            f"https://www.tiktok.com/music/{music_name.replace(' ', '-')}-{music_id}"
        )

        processed_items.append(
            {"text": text, "author": author_name, "music_url": music_url}
        )
    return processed_items


def save_posts_in_chunks(processed_items, profile, chunk_size=100, max_retries=3):
    existing_music_urls = get_existing_music_urls()

    for i in range(0, len(processed_items), chunk_size):
        logger.info("post")
        logger.info(processed_items[0])
        chunk = filter_general_posts(
            processed_items[i : i + chunk_size], existing_music_urls
        )
        retry_count = 0

        while chunk and retry_count < max_retries:
            try:
                created_posts = MusicPost.objects.bulk_create(
                    [MusicPost(**item, profile_url=profile) for item in chunk],
                    ignore_conflicts=True,
                )
                threads = []

                for music_post in created_posts:
                    threads.append(
                        threading.Thread(
                            target=process_sound_data, args=(music_post.id,)
                        )
                    )
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
                break
            except IntegrityError:
                retry_count += 1
                existing_music_urls = get_existing_music_urls()
                chunk = filter_general_posts(chunk, existing_music_urls)


def chunked_generator(generator, chunk_size):
    """Yield successive chunks from the generator."""
    chunk = []
    for item in generator:
        chunk.append(item)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def download_video(profile: Profile, video_post: VideoPost):
    if not video_post.download_video_url:
        logger.info(f"download_video_url is none or video is not None, {video_post.pk}")
    logger.info(f"Starting download of the video, {video_post.download_video_url}")

    response = requests.get(video_post.download_video_url, stream=True)

    if response.status_code == 200:
        logger.info(
            f"Starting download of the video, response: 200, {video_post.download_video_url}"
        )
        video_file_name = f"{profile.profile_name}/{video_post.download_video_id}.mp4"

        video_file = ContentFile(response.content)

        logger.info(f"Successfully downloaded video {video_post.download_video_url}")
        return video_file_name, video_file
    else:
        logger.error(f"Response error,  url: {video_post.download_video_url}")


def download_and_archive_videos(profile: Profile):
    logger.info(f"Started archiving videos for profile {profile}")
    video_posts = VideoPost.objects.filter(
        retrieved_from_post__profile_url=profile, status=VideoPost.STATUS_CREATED
    )

    # Create a BytesIO object to store the zip archive in memory
    in_memory_zip = BytesIO()
    threads = []
    for video_post in video_posts:
        thread = ThreadWithReturnValue(
            target=download_video, args=(profile, video_post)
        )
        thread.start()
        threads.append(thread)

    with ZipFile(in_memory_zip, "w") as zipf:
        for thread in threads:
            result = thread.join()
            if result:
                video_file_name, video_file = result
                # Add the video file to the ZIP file
                zipf.writestr(video_file_name, video_file.read())

    # Position the cursor at the start of the BytesIO object
    in_memory_zip.seek(0)

    # Save the zip archive to the video_archive field of the MusicPost
    archive_name = f"{profile.profile_name}.zip"
    profile.video_archive.save(archive_name, ContentFile(in_memory_zip.getvalue()))

    # Close the BytesIO object
    in_memory_zip.close()

    logger.info(f"Successfully archived videos for profile {profile}")
    video_posts.update(status=VideoPost.STATUS_UPLOADED)
