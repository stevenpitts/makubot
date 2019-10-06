cd snekbox
docker build \
    -t pythondiscord/snekbox:latest \
    -f docker/Dockerfile \
    .

docker build \
    -t pythondiscord/snekbox-base:latest \
    -f docker/base.Dockerfile \
    .

docker build \
    -t pythondiscord/snekbox-venv:latest \
    -f docker/venv.Dockerfile \
    .

docker-compose up
