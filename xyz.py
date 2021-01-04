import asyncio
from asyncio import CancelledError
import json
import logging.config
import os
import pathlib
from json import JSONDecodeError

import yaml
import time
import aioredis
from aioredis import Redis, Channel
import dotenv

from quart import Quart
from quart_session import Session as QuartSession


with open(pathlib.Path(__file__).parent / "logging.conf.yaml") as logging_file:
    logging.config.dictConfig(yaml.load(logging_file, Loader=yaml.FullLoader))

logger = logging.getLogger(__name__)

app = Quart("xyz")

dotenv.load_dotenv(verbose=True)

app.secret_key = os.getenv("FLASK_SECRET")
redis_url = os.getenv("REDISTOGO_URL")
app.config["SESSION_TYPE"] = "redis"

app.config["request_number"] = 1


@app.route("/")
async def _hello() -> dict:
    request_number = app.config["request_number"]
    app.config["request_number"] = request_number + 1
    request = {
        "response": {"request_number": request_number},
        "response_channel": f"myreplychannel{request_number}",
    }
    response = await redis_request_reply(
        redis=app.config["SESSION_REDIS"],
        request=json.dumps(request),
        request_channel="mychannel",
        reply_channel=f"myreplychannel{request_number}",
    )

    return {"message": "Hello, World!", "response": response}


@app.before_serving
async def start_redis_listener():
    app.config["SESSION_REDIS"] = await aioredis.create_redis_pool(redis_url)
    QuartSession(app)

    loop = asyncio.get_event_loop()

    async def task(redis: Redis):
        channel: [Channel, None] = None
        try:
            channel, *_ = await redis.subscribe("mychannel")

            async for message in channel.iter(encoding="utf-8"):
                try:
                    message = json.loads(message)
                except JSONDecodeError:
                    pass
                logger.debug(f"request from: {str(channel.name)}: {message}")
                # add some delay
                time.sleep(0.5)
                if isinstance(message, dict):
                    response_channel, response = (
                        message["response_channel"],
                        message["response"],
                    )
                    logger.debug(
                        f"sending response: {response} to channel {response_channel}"
                    )
                    received_count = await redis.publish_json(
                        response_channel, response
                    )
                    logger.debug(f"received by {received_count} consumers")

                else:
                    logger.debug("message isn't a dict")

        except CancelledError:
            pass
        finally:
            if channel:
                await redis.unsubscribe(channel.name)

    loop.create_task(task(app.config["SESSION_REDIS"]))


async def redis_request_reply(redis, request, request_channel, reply_channel):
    """
    Sends a message to a Redis channel, then waits for a singular reply

    :param redis: the redis to use
    :param request: the message to send - if a dict, then it is first JSON serialised
    :param request_channel: the channel to send the request to
    :param reply_channel: the channel on which to wait for a reply
    :return: the response received, JSON decoded unless it's not valid JSON
    """
    channel: Channel
    channel, *_ = await redis.subscribe(reply_channel)
    try:
        if isinstance(request, dict):
            request = json.dumps(request)
        received_count = await redis.publish(request_channel, request)
        if not received_count:
            logger.warning(
                f'message "{request}" sent to channel {request_channel} was not received by any subscriber'
            )
            # TODO should we bail at this point?
            # probably - or put in some retries
        else:
            logger.debug(
                f'message "{request}" was received by {received_count} consumers'
            )

        async def one_message():
            logger.debug(f"waiting for one message on channel {channel.name}...")
            async for message in channel.iter(encoding="utf-8"):
                logger.debug(f"received response {message}")
                return json.loads(message)

        return await asyncio.wait_for(one_message(), timeout=5)
    finally:
        if channel:
            redis.unsubscribe(channel.name)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
