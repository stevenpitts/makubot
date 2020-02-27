FROM python:3.8

WORKDIR /usr/src/app

RUN apt-get -yqq update && apt-get -yqq install ffmpeg awscli postgresql-client

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

ENV s3_bucket makumistake

COPY . .

CMD [ "python3.8", "-m", "src", "test" ]
