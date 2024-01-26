import backoff
from apify_client import ApifyClient as ApifySDKClient
from django.conf import settings


class BaseApifyClient:
    def __init__(self):
        self.client = ApifySDKClient(settings.APIFY_API_TOKEN)

    _run = None

    @backoff.on_exception(backoff.expo, Exception, max_tries=5)
    def run_actor(self, actor_id, run_input):
        self._run = self.client.actor(actor_id).call(run_input=run_input)
        return self.client.dataset(self._run["defaultDatasetId"]).iterate_items()


class TikTokScrapperClient(BaseApifyClient):
    ACTOR_ID = "GdWCkxBtKWOsKjdch"

    def run(self, run_input):
        return self.run_actor(self.ACTOR_ID, run_input)


class TikTokSoundScraperClient(BaseApifyClient):
    ACTOR_ID = "JVisUAY6oGn2dBn99"

    def run(self, run_input):
        return self.run_actor(self.ACTOR_ID, run_input)


class TikTokVideoDownloadClient(BaseApifyClient):
    ACTOR_ID = "5AnFmBqPofhuiqvaf"
    STORAGE_ID = None

    def run(self, run_input):
        run_generator = self.run_actor(self.ACTOR_ID, run_input)
        self.STORAGE_ID = self._run["defaultKeyValueStoreId"]
        return run_generator

    def get_download_video_url(self, video_id):
        return (
            f"https://api.apify.com/v2/key-value-stores"
            f"/{self.STORAGE_ID}/records/{video_id}"
        )
