set -e
# function error() {
#     JOB="$0"              # job name
#     LASTLINE="$1"         # line of error occurrence
#     LASTERR="$2"          # error code
#     echo "ERROR in ${JOB} : line ${LASTLINE} with exit code ${LASTERR}"
#     exit 1
# }
# trap 'error ${LINENO} ${?}' ERR

trap 'docker-compose down' ERR

export bot_name="${bot_name:-makumistake}"
export s3_bucket="${s3_bucket:-$bot_name}"
export credentials_secret_name="${credentials_secret_name:-$bot_name}"
export db_name="${db_name:-mb_db}"
export db_port="${db_port:-5432}"
export container_network="${container_network:-${bot_name}_network}"

credentials=`aws secretsmanager get-secret-value \
  --secret-id $credentials_secret_name \
  --query SecretString \
  --output text`

export bot_access_key=`echo $credentials | jq -r ".AWS_ACCESS_KEY_ID"`
export bot_secret_key=`echo $credentials | jq -r ".AWS_SECRET_ACCESS_KEY"`
export google_api_key=`echo $credentials | jq -r ".GOOGLE_API_KEY"`
export discord_token=`echo $credentials | jq -r ".DISCORD_TOKEN"`
export pgpassword=`echo $credentials | jq -r ".PGPASSWORD"`

docker-compose up --build --abort-on-container-exit --exit-code-from bot

docker-compose down
#
#
# docker build --tag makubot . &
#
#
# # Neither snekbox nor postgres get stopped or removed after script ends,
# # so be careful
# docker container rm -f snekbox 2>/dev/null && echo "Stopped Snekbox" || true &
# docker container rm -f $db_name 2>/dev/null && echo "Stopped $db_name" || true &
# wait
# docker network rm $container_network 2>/dev/null \
#   && echo "Stopped $container_network" || true
#
# docker network create $container_network &
# docker pull pythondiscord/snekbox &
# docker pull postgres &
# wait
#
# docker run -d --name "$db_name" \
#   --network $container_network \
#   --env POSTGRES_PASSWORD="$pgpassword" \
#   postgres &
#
# docker run -d --name snekbox --privileged --init --ipc="none" \
#   --network $container_network \
#   pythondiscord/snekbox &
#
# wait
#
# db_ip=$(docker container inspect makumistake_db \
#   | jq -r ".[0].NetworkSettings.Networks.$container_network.IPAddress")
#
# while ! nc -z $db_ip $db_port; do
#   echo waiting
#   sleep 0.1 # wait for 1/10 of the second before check again
# done
#
#
# docker run -it --rm --name $bot_name --network $container_network \
#   --env AWS_ACCESS_KEY_ID=$bot_access_key \
#   --env AWS_SECRET_ACCESS_KEY=$bot_secret_key \
#   --env DISCORD_BOT_TOKEN=$discord_token \
#   --env GOOGLE_API_KEY=$google_api_key \
#   --env S3_BUCKET=$s3_bucket \
#   --env PGPASSWORD=$pgpassword \
#   --env PGHOST=$db_ip \
#   --env PGPORT=$db_port \
#   --env PGUSER=postgres \
#   makubot
