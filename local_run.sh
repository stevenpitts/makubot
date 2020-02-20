set -e

# snekbox doesn't get stopped or removed after script ends, so be careful

docker container rm -f snekbox 2>/dev/null && echo "Stopped Snekbox" || true
docker pull pythondiscord/snekbox-base \
  && docker run -d --name snekbox --privileged --hostname pdsnk \
    --init --ipc="none" -p8060:8060 pythondiscord/snekbox

bot_name="${bot_name:-makumistake}"
s3_bucket="${s3_bucket:-$bot_name}"
credentials_secret_name="${credentials_secret_name:-$bot_name}"

docker build --tag makubot .

credentials=`aws secretsmanager get-secret-value \
  --secret-id $credentials_secret_name \
  --query SecretString \
  --output text`

bot_access_key=`echo $credentials | jq -r ".AWS_ACCESS_KEY_ID"`
bot_secret_key=`echo $credentials | jq -r ".AWS_SECRET_ACCESS_KEY"`

docker run -it --rm --name $bot_name \
  -e AWS_ACCESS_KEY_ID=$bot_access_key \
  -e AWS_SECRET_ACCESS_KEY=$bot_secret_key \
  -e s3_bucket=$s3_bucket \
  --network="host" \
  makubot
