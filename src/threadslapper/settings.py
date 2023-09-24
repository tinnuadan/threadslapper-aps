import logging
import os
import sys
from typing import Annotated

import yaml
from pydantic import AfterValidator, BaseModel, SecretStr, BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


def prevalidate_boolean(v) -> bool:
    """Evaluate 'true' strings to True, everything else to False"""
    if v is None:
        return False
    if isinstance(v, str):
        if v.lower() in ['true', 't', 'yes', 'y', '1']:
            return True
        else:
            return False
    return v


def validate_string(v: str) -> str:
    """Remove unwanted whitespace and check for quotation marks"""
    v = v.strip()
    assert '"' not in v, "Quotation symbol `\"` detected, please remove."
    assert "'" not in v, "Quotation symbol `\'` detected, please remove."
    return v


def validate_secretstr(v: SecretStr) -> SecretStr:
    """Remove unwanted whitespace and check for quotation marks"""
    _v = v.get_secret_value()
    _v = _v.strip()
    if '"' in _v:
        raise AssertionError("Quotation symbol `\"` detected, please remove.")
    if "'" in _v:
        raise AssertionError("Quotation symbol `\"` detected, please remove.")
    return SecretStr(_v)


class RssFeedToChannel(BaseModel):
    enabled: Annotated[bool, BeforeValidator(prevalidate_boolean)] = True
    title_prefix: Annotated[str, AfterValidator(validate_string)] = ""
    title: Annotated[str, AfterValidator(validate_string)] = "default"
    channel_id: int = -1
    rss_feed: Annotated[str, AfterValidator(validate_string)] = ""

    # keys to pick out of the rss xml document
    rss_episode_key: Annotated[str, AfterValidator(validate_string)] = "itunes_episode"
    rss_title_key: Annotated[str, AfterValidator(validate_string)] = "itunes_title"
    rss_description_key: Annotated[str, AfterValidator(validate_string)] = "subtitle"
    rss_image_key: Annotated[str, AfterValidator(validate_string)] | None = "image"
    rss_tag_key: Annotated[str, AfterValidator(validate_string)] = "tags"

    # Use this for overriding patroen RSS feed GUIDs
    override_episode_numbers: Annotated[bool, BeforeValidator(prevalidate_boolean)] = False
    current_episode: int = 0


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="threadslapper_",
        env_nested_delimiter="__",
        env_file=".env",
    )

    token: Annotated[SecretStr, AfterValidator(validate_secretstr)] = SecretStr("foo")
    check_interval_min: int = 5
    log_path: Annotated[str, AfterValidator(validate_string)] = "."
    config_path: Annotated[str, AfterValidator(validate_string)] = "config/"
    config_file: Annotated[str, AfterValidator(validate_string)] = "example_config.yml"
    startup_latest_episode_check: bool = True  # check for latest episodes on power on

    # A single RSS feed can be defined, or a list of yaml objects
    channel: RssFeedToChannel | None = None
    channels_file: str | None = None

    def create_logger(self, name: str) -> logging.Logger:
        log = logging.getLogger(name)
        log.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        stdout = logging.StreamHandler(sys.stdout)
        stdout.level = logging.INFO
        stdout.setFormatter(formatter)
        file = logging.FileHandler(os.path.join(self.log_path, 'discordbot.log'))
        file.level = logging.INFO
        file.setFormatter(formatter)
        log.addHandler(stdout)
        log.addHandler(file)

        return log

    def get_channels_list(self) -> list[RssFeedToChannel]:
        """
        Parses the config yaml file.
        """
        obj = {}
        config_file = os.path.join(self.config_path, self.config_file)
        if os.path.exists(config_file):
            with open(config_file, mode='r') as f:
                obj = yaml.safe_load(f)

        feeds: list[RssFeedToChannel] = []
        if self.channel:
            feeds.append(self.channel)

        for key, value in obj.items():
            rss = RssFeedToChannel(
                enabled=value.get('enabled', True),
                title=key,
                title_prefix=value.get('title_prefix', ''),
                channel_id=value.get('channel_id', -1),
                rss_feed=value.get('rss_url', ''),
                override_episode_numbers=value.get('override_episode_numbers', False),
            )
            if (rss_key := value.get('rss_episode_key', None)) is not None:
                rss.rss_episode_key = rss_key
            if (rss_key := value.get('rss_title_key', None)) is not None:
                rss.rss_title_key = rss_key
            if (rss_key := value.get('rss_description_key', None)) is not None:
                rss.rss_description_key = rss_key
            if (rss_key := value.get('rss_image_key', None)) is not None:
                rss.rss_image_key = rss_key
            if (rss_key := value.get('rss_tag_key', None)) is not None:
                rss.rss_tag_key = rss_key

            if rss.channel_id > -1 and rss.rss_feed != '':
                feeds.append(rss)
            else:
                raise ValueError(f"Please check '{rss.title}' for incorrect configuration")

        return feeds
