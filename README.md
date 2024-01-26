# tiktokparser

## Installation prerequisites for Macos

### Install the docker
#### After downloading Docker.dmg, run the following commands in a terminal to install Docker Desktop in the Applications folder:
```
sudo hdiutil attach Docker.dmg
sudo /Volumes/Docker/Docker.app/Contents/MacOS/install
sudo hdiutil detach /Volumes/Docker
```
#### As macOS typically performs security checks the first time an application is used, the ```install``` command can take several minutes to run.
#### The ```install``` command accepts the following flags:
```
--accept-license: accepts the Docker Subscription Service Agreement now, rather than requiring it to be accepted when the application is first run
--allowed-org=<org name>: requires the user to sign in and be part of the specified Docker Hub organization when running the application
--user=<username>: Runs the privileged helper service once during installation, then disables it at runtime. This removes the need for the user to grant root privileges on first run. For more information, see Privileged helper permission requirements. To find the username, enter ls /Users in the CLI.
```
#### In case of errors use the link below
```
https://docs.docker.com/desktop/install/mac-install/
```

## Running locally using docker-compose

### 1. Create .env file.
```bash
AUTH_TOKEN=<Key from finnhub>
DJANGO_DEBUG=True
DATABASE_URL=postgres://postgres:postgres@db:5432/postgres  # sqlite by default
ENVIRONMENT=development
```

### 2. Create general.log file in root directory.

### 3. Run all services at once (Django, Postgres, Redis, Celery)
```bash
docker-compose up -d --build
```

### 4. Check status of containers
```bash
docker ps -a  # all containers
docker logs -f -t tiktokparser_admin  # logs of particular container
```

### 5. Try visit [Django admin panel](http://127.0.0.1:8000/admin/)

### 6. Enter django shell and create superuser
```bash
docker exec -it tiktokparser_admin bash
python manage.py createsuperuser
```

### 6. To stop all containers
```bash
docker-compose stop
```

## API
```bash
GET
http://127.0.0.1:8000/api/news/NFLX/?date_from=2022-10-12&date_to=2022-10-15
RESPONSE:
[
    {
        "id": 19,
        "headline": "Meta Platforms: Mark Zuckerberg Just Scored A Big Win For The Metaverse",
        "published_datetime": "2022-10-13T16:25:30Z",
        "summary": "Meta's \"Project Cambria\" reveal finally happened and the new device Quest Pro will be ready to ship in late October. See our sentiments on META stock.",
        "source": "SeekingAlpha"
    },
    {
        "id": 20,
        "headline": "Streaming's Success Propels Real Estate Investment",
        "published_datetime": "2022-10-13T03:00:22Z",
        "summary": "The film industry has come a long way from the back lots of Burbank. Hackman Capital Partners, a real estate investment firm, is gearing up to...",
        "source": "Yahoo"
    },
    {
        "id": 32,
        "headline": "Apple Looks To Go Deep As Its Expands Presence In A Growing Area",
        "published_datetime": "2022-10-14T07:30:00Z",
        "summary": "Apple's (AAPL) end-goal is more hardware-centric than subscription-based, allowing it innovative, creative and often costly moves. See how sports fits in here.",
        "source": "SeekingAlpha"
    },
    {
        "id": 33,
        "headline": "Wall Street Breakfast: Mr. Market's Wild Ride",
        "published_datetime": "2022-10-14T06:32:26Z",
        "summary": "Listen on the go! A daily podcast of Wall Street Breakfast will be available by 8:00 a.m. on Seeking Alpha, iTunes, Stitcher and Spotify. Mr.",
        "source": "SeekingAlpha"
    },
    {
        "id": 34,
        "headline": "PRESS DIGEST-British Business - Oct 14",
        "published_datetime": "2022-10-14T00:44:56Z",
        "summary": "The following are the top stories on the business pages of British newspapers.  - BT Group and other phone operators have been given another year to strip out Huawei technology from core 5G networks to avoid causing serious disruption to customers, the government said.  - Data unveiled on Thursday showed GSK's respiratory syncytial virus (RSV) vaccine was 82.6% effective in a keenly watched late-stage study involving older adults.",
        "source": "Yahoo"
    },
    {
        "id": 35,
        "headline": "Netflix Earnings Preview: Can NFLX Get its Mojo Back?",
        "published_datetime": "2022-10-14T00:10:12Z",
        "summary": "The company's earnings are always heavily covered with the stock tending to have big movements in either direction after reporting. The direction of the stock usually hinges on the company's guidance for subscriber growth above all else.",
        "source": "Yahoo"
    }
]

```
