FROM ubuntu:18.04

# postgresql installs tzdata which wants interactive config, squash that
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && \
    apt-get -yq install \
        python3.7 python3-venv python3.7-venv python3-pip python3-wheel python3-dev \
        git \
        wait-for-it \
        vim && \
    mkdir /app && \
    cd /app && \
    python3.7 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip wheel && \
    echo . /app/venv/bin/activate >> ~/.bashrc

WORKDIR app

# copy python requirements, and install them
COPY requirements.txt /app

RUN . venv/bin/activate && \
    pip install -r requirements.txt

# copy everything else
COPY . /app

ENV REDISTOGO_URL redis://:@redis:6379

ENV QUART_APP=xyz:app
EXPOSE 5000
CMD . /app/venv/bin/activate && \
    wait-for-it redis:6379 -- quart run --host 0.0.0.0
