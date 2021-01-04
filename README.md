# Redis PubSub with Quart
Sample Quart app with a redis based pub/sub.

A single endpoint, `/` is exposed, which sends a numbered message to a
redis channel and waits for a response, which is then spat out.  The receiver 
on the other end is simply iterating over the (never ending) list of available 
messages, and after sleeping for 0.5 seconds (to simulate something actually 
doing something), responds.


## Setup
Create a `.env` file and put the following in
```shell script
FLASK_SECRET='some secret here'
```

Then run the following:

```shell script
python -m venv venv
. venv/bin/activate
pip install --upgrade pip
pip install wheel
pip install -r requirements.txt
```

## Running the server
```shell script
docker-compose build
docker-compose up
```

## Invoking it
```shell script
curl localhost:5000/ & curl localhost:5000/ & curl localhost:5000/ & 
```
This will spit out 3 requests rapid fire.
