source ./prepare_vars.sh

if docker-compose exec mbdb echo hi > /dev/null 2>&1
then
    docker-compose exec -u postgres mbdb pg_dump | aws s3 cp - "s3://${s3_bucket}/backups/$(date +"%Y.%m.%d.%H.%M.%S").runremote.pgdump"
fi

docker-compose up --build --remove-orphans --detach --no-recreate mbdb snekbox

docker-compose up --build --remove-orphans --detach bot
