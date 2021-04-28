#!/usr/bin/env python3

"""
Entrypoint to running the bot server process.

Handles notification endpoints and responds with messages or other actions
where required.

"""

import argparse
import logging
import os
import sys

import requests
from flask import Flask, request
from requests_toolbelt import MultipartEncoder

logger = logging.getLogger(__name__)

# Set in main().
BOT_ACCESS_TOKEN = None

BASE_URL = "https://api.ciscospark.com/v1"

app = Flask(__name__)


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------


def get_message(msg_id: str) -> str:
    response = requests.get(
        f"{BASE_URL}/messages/{msg_id}",
        headers={"Authorization": f"Bearer {BOT_ACCESS_TOKEN}"},
    )
    response.raise_for_status()
    return response.json()["text"]


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------


@app.route("/message", methods=["POST"])
def message_handler():
    """Receive notification of a bot message."""
    data = request.get_json()["data"]
    logger.debug("Got bot message notification: %s", data)

    user = data["personEmail"]
    msg_id = data["id"]
    person_id = data["personId"]
    try:
        msg_text = get_message(msg_id)
        logger.debug("Fetched message content: %r", msg_text)
    except requests.HTTPError:
        logger.exception(f"Error getting message from {user}")
        raise

    msg = f"I'm *very* excited by your message, {user}"
    multipart = MultipartEncoder({"markdown": msg, "personId": person_id})
    response = requests.post(
        f"{BASE_URL}/messages",
        data=multipart,
        headers={
            "Authorization": f"Bearer {BOT_ACCESS_TOKEN}",
            "Content-Type": multipart.content_type,
        },
    )
    response.raise_for_status()


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", "-p", type=int, help="Override the default port")
    parser.add_argument("--dev", action="store_true", help="Run in development mode")
    return parser.parse_args(argv)


def main(argv):
    global BOT_ACCESS_TOKEN

    args = parse_args(argv)

    logging.basicConfig(
        filename="bot-server.log",
        level=logging.DEBUG,
        format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
    )

    try:
        BOT_ACCESS_TOKEN = os.environ["BOT_ACCESS_TOKEN"]
    except KeyError:
        logger.error("No 'BOT_ACCESS_TOKEN' env var set")
        sys.exit(1)

    logger.info("Starting up")
    if args.dev:
        os.environ["FLASK_ENV"] = "development"
        app.run(debug=True, port=args.port)
    else:
        from waitress import serve

        serve(app, port=args.port)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        logger.info("Exiting on Ctrl+C")
