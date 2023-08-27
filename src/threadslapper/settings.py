import logging
import os
import sys

import yaml
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RssFeedToChannel(BaseModel):
    enabled: bool = True
    title_prefix: str = ""
    title: str = "default"
    channel_id: int = -1
    rss_feed: str = ""

    # keys to pick out of the rss xml document
    rss_episode_key: str = "itunes_episode"
    rss_title_key: str = "itunes_title"
    rss_description_key: str = "subtitle"
    rss_image_key: str = "image"
    rss_tag_key: str = "tags"

    current_episode: int = 0


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="threadslapper_",
        env_nested_delimiter="__",
        env_file=".env",
    )

    token: SecretStr = SecretStr("foo")
    check_interval_min: int = 5
    log_path: str = "."
    config_path: str = "config/"
    config_file: str = "example_config.yml"
    post_latest_episode_check: bool = True  # check for latest episodes on power on

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
