#!/usr/bin/env bash

source ./prepare_vars.sh

export AWS_ACCESS_KEY_ID=${bot_access_key}
export AWS_SECRET_ACCESS_KEY=${bot_secret_key}
export DISCORD_BOT_TOKEN=${discord_token}
export GOOGLE_API_KEY=${google_api_key}
export S3_BUCKET=${s3_bucket}
export PGPASSWORD=${pgpassword}
export PGHOST=localhost
export PGPORT=${db_port}
export PGUSER=postgres
export PGNAME=postgres

export DEVELOPMENT=1

python3.8 -m src
