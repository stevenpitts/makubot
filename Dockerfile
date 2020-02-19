FROM python:3.8

WORKDIR /usr/src/app

RUN pip install --no-cache-dir wikipedia google-api-python-client discord-py urllib3 python-dateutil youtube-dl PyNaCl boto3

COPY . .

ENV s3_bucket makubottestbucket

CMD [ "python3.8", "-m", "src", "test" ]
