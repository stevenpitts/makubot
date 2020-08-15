set -e

trap 'docker-compose down' ERR

source ./prepare_vars.sh

docker-compose up --build --remove-orphans --abort-on-container-exit --exit-code-from bot

docker-compose down
