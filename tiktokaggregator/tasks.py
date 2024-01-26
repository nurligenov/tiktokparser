import requests
from celery import shared_task
from django.core.files.base import ContentFile
from django.db.utils import IntegrityError

from clients.apify import (TikTokScrapperClient, TikTokSoundScraperClient,
                           TikTokVideoDownloadClient)

from .models import MusicPost, VideoPost


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


@shared_task
def process_sound_data(music_post_id, chunk_size=10):
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
    all_saved_successfully = True

    for raw_sound_data_chunk in chunked_generator(sound_data_generator, chunk_size):
        processed_chunk = process_sound_tiktok_results(raw_sound_data_chunk)

        video_download_client = TikTokVideoDownloadClient()
        video_posts_to_create = []
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
        for filtered_video_id in filtered_video_ids:
            download_video_url = video_download_client.get_download_video_url(
                filtered_video_id
            )
            response = requests.get(download_video_url, stream=True)
            if response.status_code == 200:
                video_file_name = (
                    f"{music_post.profile.split('/')[-1]}/{filtered_video_id}.mp4"
                )

                video_file = ContentFile(response.content)
                video_post = VideoPost(
                    retrieved_from_post=music_post,
                )
                video_post.video.save(video_file_name, video_file, save=False)
                video_posts_to_create.append(video_post)
            else:
                all_saved_successfully = False

        try:
            VideoPost.objects.bulk_create(video_posts_to_create, ignore_conflicts=True)
        except IntegrityError:
            all_saved_successfully = False
            existing_tiktok_ids = get_existing_tiktok_video_ids()

    if all_saved_successfully:
        music_post.status = MusicPost.STATUS_FINISHED
    else:
        music_post.status = MusicPost.STATUS_FAILED
    music_post.save()


@shared_task
def process_tiktok_data(run_input):
    client = TikTokScrapperClient()
    raw_items_generator = client.run(run_input)
    print(run_input)
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
        print("post")
        print(processed_items[0])
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
