#!/usr/bin/env bash

export BOT_NAME="${BOT_NAME:-makumistake}"

credentials_secret_name="${credentials_secret_name:-$BOT_NAME}"

credentials=$(aws secretsmanager get-secret-value \
  --secret-id "$credentials_secret_name" \
  --query SecretString \
  --output text)

export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY
export DISCORD_BOT_TOKEN
export PGPASSWORD
export GOOGLE_API_KEY

AWS_ACCESS_KEY_ID=$(echo "$credentials" | jq -r ".AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY=$(echo "$credentials" | jq -r ".AWS_SECRET_ACCESS_KEY")
GOOGLE_API_KEY=$(echo "$credentials" | jq -r ".GOOGLE_API_KEY")
DISCORD_BOT_TOKEN=$("echo $credentials" | jq -r ".DISCORD_TOKEN")
PGPASSWORD=$(echo "$credentials" | jq -r ".PGPASSWORD")

export S3_BUCKET="${s3_bucket:-$BOT_NAME}"
export PGHOST="${db_host:-localhost}"
export PGPORT="${db_port:-5432}"
export PGUSER="${db_user:-postgres}"
export PGNAME="${db_name:-mb_db}"

export DEVELOPMENT=1

python3.8 -m src
