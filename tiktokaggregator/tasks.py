import logging
import threading
from celery import shared_task
from django.db.utils import IntegrityError

from clients.apify import (TikTokScrapperClient, TikTokSoundScraperClient,
                           TikTokVideoDownloadClient)

from .models import MusicPost, VideoPost


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


def save_video_post(client: TikTokVideoDownloadClient, video_id, music_post):
    download_video_url = client.get_download_video_url(
        video_id
    )
    logger.info(f"Going to save video {download_video_url}")
    try:
        video_post = VideoPost(
            retrieved_from_post=music_post,
            download_video_id=video_id,
            download_video_url=download_video_url,
        )
        video_post.save()
        logger.info(f"Saved video {download_video_url}, profile: {music_post.profile}")
    except IntegrityError:
        logger.error(f"IntegrityError during saving video {download_video_url}, profile: {music_post.profile}")
    except Exception as e:
        logger.error(f"Error during saving video {download_video_url}, profile: {music_post.profile}, e: {e}")
    return False


@shared_task
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
        threads = []
        for filtered_video_id in filtered_video_ids:
            threads.append(threading.Thread(target=save_video_post, args=(video_download_client, filtered_video_id, music_post)))
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    music_post.status = MusicPost.STATUS_FINISHED
    music_post.save()


@shared_task
def process_tiktok_data(run_input):
    client = TikTokScrapperClient()
    raw_items_generator = client.run(run_input)
    logger.info(run_input)
    profile = run_input["profiles"][0]

    # Process items from the generator
    for raw_items_chunk in chunked_generator(raw_items_generator, chunk_size=100):
        processed_items = process_tiktok_results(raw_items_chunk)
        save_posts_in_chunks(processed_items, profile)


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
                    [MusicPost(**item, profile=profile) for item in chunk],
                    ignore_conflicts=True,
                )
                for music_post in created_posts:
                    process_sound_data.delay(
                        music_post.id
                    )  # Call the task for each created MusicPost
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
