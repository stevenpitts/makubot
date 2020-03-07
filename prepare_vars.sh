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