source ./prepare_vars.sh

docker-compose up --build --detach --no-recreate mbdb snekbox

docker-compose up --build --detach bot
