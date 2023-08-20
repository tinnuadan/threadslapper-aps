import logging
import os
import sys

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    token: SecretStr = SecretStr("foo")
    forum_channel_name: str = "this-weeks-episode"

    rss_feed: str = ""

    check_interval_min: int = 5  # Only check once an hour

    model_config = SettingsConfigDict(env_prefix="threadslapper_")

    log_path: str = "."

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
