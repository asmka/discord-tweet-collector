import pytest

from tcbot.exception import TCBotError
from tcbot.twauth import TwitterAuth


def test_initialize_invalid_consumer_key(config):
    with pytest.raises(TCBotError, match=r"Failed to authenticate twitter api\."):
        TwitterAuth(
            "INVALID_CONSUMER_KEY",
            config.consumer_secret,
            config.access_token,
            config.access_secret,
        )


def test_initialize_invalid_consumer_secret(config):
    with pytest.raises(TCBotError, match=r"Failed to authenticate twitter api\."):
        TwitterAuth(
            config.consumer_key,
            "INVALID_CONSUMER_SECRET",
            config.access_token,
            config.access_secret,
        )


def test_initialize_invalid_access_token(config):
    with pytest.raises(TCBotError, match=r"Failed to authenticate twitter api\."):
        TwitterAuth(
            config.consumer_key,
            config.consumer_secret,
            "INVALID_ACCESS_TOKEN",
            config.access_secret,
        )


def test_initialize_invalid_access_secret(config):
    with pytest.raises(TCBotError, match=r"Failed to authenticate twitter api\."):
        TwitterAuth(
            config.consumer_key,
            config.consumer_secret,
            config.access_token,
            "INVALID_ACCESS_SECRET",
        )
