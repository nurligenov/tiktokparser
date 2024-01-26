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
DJANGO_DEBUG=True
DATABASE_URL=postgres://postgres:postgres@db:5432/postgres  # sqlite by default
ENVIRONMENT=development
DJANGO_AWS_STORAGE_BUCKET_NAME=
DJANGO_AWS_ACCESS_KEY_ID=
DJANGO_AWS_SECRET_ACCESS_KEY=
APIFY_API_TOKEN=
```

### 2. Run all services at once (Django, Postgres, Redis, Celery)
```bash
docker-compose up -d --build
```

### 3. Check status of containers
```bash
docker ps -a  # all containers
docker logs -f -t tiktokparser_admin  # logs of particular container
```

### 4. Try visit [Django admin panel](http://127.0.0.1:8000/admin/)

### 5. Enter django shell and create superuser
```bash
docker exec -it tiktokparser_admin bash
python manage.py createsuperuser
```

### 6. To stop all containers
```bash
docker-compose stop
```
