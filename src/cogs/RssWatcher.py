from io import BytesIO

import feedparser
import urllib3
from discord import Bot, ChannelType, File, ForumChannel, ForumTag, TextChannel
from discord.abc import GuildChannel
from discord.ext import commands, tasks
from pydantic import BaseModel, Field

from threadslapper.settings import Settings

settings = Settings()
log = settings.create_logger('RssWatcher')


class EpisodeData(BaseModel):
    number: int
    title: str
    description: str
    image: bytes = Field(..., repr=False)
    tags: list[str]


class RssWatcher(commands.Cog):
    def __init__(self, bot, rss_feed: str, forum_channel_name: str, starting_episode_number: int = 0):
        self.bot = bot
        if not rss_feed:
            raise ValueError("RSS Feed must not be empty!")
        self.rss_feed = rss_feed
        if not forum_channel_name:
            raise ValueError("Forum Channel Name must not be empty!")
        self.forum_channel_name = forum_channel_name
        self._current_episode = starting_episode_number

    def cog_unload(self):
        self.check_rss_feed.cancel()

    def _check_for_new_episode(self) -> EpisodeData:
        data = feedparser.parse(self.rss_feed)

        latest_episode = data.entries[0]
        http = urllib3.PoolManager()
        img = http.request("GET", latest_episode.image.href).data

        return_data = EpisodeData(
            number=latest_episode.itunes_episode,
            title=latest_episode.itunes_title,
            description=latest_episode.subtitle,
            image=img,
            tags=[tag.term for tag in latest_episode.tags],
        )

        return return_data

    def check_rss(self, episode_number_override: int | None = None) -> EpisodeData | None:
        current_episode = episode_number_override or self._current_episode

        new_episode = self._check_for_new_episode()

        if new_episode.number > current_episode:
            self._current_episode = new_episode.number
            return new_episode
        return None

    def get_this_weeks_episode_channel_id(self, channel_name: str) -> list[GuildChannel]:
        """
        Gets all channels matching our targetted channel name.

        Should be one or none, could be more /shrug
        """
        channels = []

        if not channel_name:
            raise ValueError("Channel name cannot be blank!")

        log.info(f"Looking for channel '{channel_name}'...")
        for channel in self.bot.get_all_channels():
            if channel_name in channel.name:
                log.info(f"Found '{channel_name}' in '{channel}', (id: {channel.id}, type: {type(channel)})")
                channels.append(channel)

        return channels

    @tasks.loop(minutes=settings.check_interval_min)
    async def check_rss_feed(self):
        log.info("Checking RSS feed...")
        try:
            new_episode = self.check_rss()

            if new_episode:
                log.info(f"New episode found: {new_episode.number}")

                channels = self.get_this_weeks_episode_channel_id(self.forum_channel_name)
                img = File(fp=BytesIO(new_episode.image), filename="thumbnail.png")
                for channel in channels:
                    if isinstance(channel, TextChannel):
                        message = await channel.send(
                            content=new_episode.description,
                            file=img,
                        )
                        await channel.create_thread(
                            message=message,
                            name=new_episode.title,
                            type=ChannelType.public_thread,
                            reason=f"New Episode ({new_episode.number}) detected, creating thread.",
                        )
                    elif isinstance(channel, ForumChannel):
                        await channel.create_thread(
                            content=new_episode.description,
                            message=message,
                            name=new_episode.title,
                            type=ChannelType.public_thread,
                            file=img,
                            tags=[ForumTag(name=tag) for tag in new_episode.tags],
                            reason=f"New Episode ({new_episode.number}) detected, creating thread.",
                        )
                    log.info(f"Channel '{new_episode.title}' created!")
            else:
                log.info('No updates.')
        except ValueError as e:
            log.error(e)


def setup(bot: Bot):
    rsswatcher = RssWatcher(bot, settings.rss_feed, settings.forum_channel_name)
    bot.add_cog(rsswatcher)
