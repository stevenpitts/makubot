FROM python:3.8

WORKDIR /usr/src/app

RUN apt-get -yqq update && apt-get -yqq install ffmpeg awscli postgresql-client \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

HEALTHCHECK CMD discordhealthcheck || exit 1

COPY src ./src

CMD python3.8 -m src
