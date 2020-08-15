source ./prepare_vars.sh

docker-compose up --build --remove-orphans --detach --no-recreate mbdb snekbox

docker-compose up --build --remove-orphans --detach bot
