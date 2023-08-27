"""
RssWatcher,

Watches RSS feeds for new episodes then posts a discord message/thread/post.
"""

from io import BytesIO

import feedparser
import urllib3
from discord import Bot, ChannelType, File, ForumChannel, ForumTag, TextChannel, channel
from discord.abc import GuildChannel
from discord.ext import commands, tasks
from markdownify import markdownify as md
from pydantic import BaseModel, Field

from threadslapper.settings import RssFeedToChannel, Settings

settings = Settings()
log = settings.create_logger('RssWatcher')


class EpisodeData(BaseModel):
    number: int
    title: str
    description: str
    image: bytes | None = Field(..., repr=False)
    tags: list[str]  # this doesn't work, ignore it for now

    def get_description(self):
        """Converts an HTML formatted document to markdown, limits text to 2000 in length"""
        desc = md(self.description)
        if len(desc) > 2000:
            desc = f"{desc[:1997]}..."

        return desc

    def get_title(self, prefix: str = ""):
        """
        Appends a prefix to a title to make it clear what feed it comes from,
        if the title of the episode does not contain an episode number, prepend
        the episode number in the RSS feed to the episode title.
        """
        if self.title.startswith(f"{self.number}"):
            return f"{prefix} {self.title}".strip()
        return f"{prefix} {self.number}: {self.title}".strip()


class RssWatcher(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.feeds = settings.get_channels_list()

        log.info(f'Beginning first time check of RSS feed... {", ".join([feed.title for feed in self.feeds])}')
        if settings.post_latest_episode_check:
            for feed in self.feeds:
                if (latest_episode := self.check_rss(rss=feed)) is not None:
                    log.info(f'{feed.title}: Latest episode checked on bot power on: {latest_episode.number}.')
                else:
                    raise RuntimeError(f"{feed.title}: No episode data found! Please check RSS Feed URL")

    def cog_unload(self):
        self.check_rss_feed.cancel()

    def _get_latest_episode_data(self, rss: RssFeedToChannel) -> EpisodeData:
        """Gets the data for the latest episode"""
        data = feedparser.parse(rss.rss_feed)

        latest_episode = data.entries[0]
        http = urllib3.PoolManager()
        img = http.request("GET", latest_episode.get(rss.rss_image_key, {}).href.replace('large', 'small')).data

        return_data = EpisodeData(
            number=latest_episode.get(rss.rss_episode_key, 0),
            title=latest_episode.get(rss.rss_title_key, "None"),
            description=latest_episode.get(rss.rss_description_key, "None"),
            image=img,
            tags=[tag.term for tag in latest_episode.get(rss.rss_tag_key, [])],
        )

        return return_data

    def check_rss(self, rss: RssFeedToChannel, episode_number_override: int | None = None) -> EpisodeData | None:
        """
        If the latest episode is newer than the currently stored episode,
        return new episode
        """
        current_episode = episode_number_override or rss.current_episode

        new_episode = self._get_latest_episode_data(rss)

        if new_episode.number > current_episode:
            rss.current_episode = new_episode.number
            return new_episode
        return None

    @tasks.loop(minutes=settings.check_interval_min)
    async def check_rss_feed(self):
        """Actual bot loop"""
        log.info("Checking RSS feed...")
        for feed in self.feeds:
            if feed.enabled is False:
                log.info(f'{feed.title}: Is disabled, skipping.')
                continue
            try:
                if (new_episode := self.check_rss(rss=feed)) is not None:
                    log.info(f"{feed.title}: New episode found: {new_episode.number}")

                    channel = self.bot.get_channel(feed.channel_id)
                    img = File(fp=BytesIO(new_episode.image), filename="thumbnail.png")
                    title = new_episode.get_title(feed.title_prefix)

                    if isinstance(channel, TextChannel):
                        # If the channel is a regular text channel, spawn a thread
                        message = await channel.send(
                            content=new_episode.get_description(),
                            file=img,
                        )
                        await channel.create_thread(
                            message=message,
                            name=title,
                            type=ChannelType.public_thread,
                            reason=f"{feed.title}: New Episode ({new_episode.number}) detected, creating thread: {title}",
                        )

                    elif isinstance(channel, ForumChannel):
                        # If the channel is a Forum, spawn a post (that is actually a thread)
                        if not title in [thread.name for thread in channel.threads]:
                            new_thread = await channel.create_thread(
                                name=title,
                                content=new_episode.get_description(),
                                reason=f"{feed.title}: New Episode ({new_episode.number}) detected, creating thread: {title}",
                            )
                            # Annoyingly I can't attach an image or remove embedded links on thread creation
                            message = new_thread.starting_message
                            await message.edit(file=img, suppress=True)
                            log.info(f"{feed.title}: Channel '{new_episode.title}' created!")
                        else:
                            log.info(f"{feed.title}: Channel '{new_episode.title}' already exists, doing nothing.")
                else:
                    log.info(f'{feed.title}: No updates.')
            except Exception as e:
                log.error(e)


def setup(bot: Bot):
    rsswatcher = RssWatcher(bot)
    bot.add_cog(rsswatcher)
