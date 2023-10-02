"""
RssWatcher,

Watches RSS feeds for new episodes then posts a discord message/thread/post.
"""

from datetime import datetime

import feedparser
from discord import Bot, ChannelType, Color, Embed, ForumChannel, TextChannel, Thread
from discord.ext import commands, tasks
from markdownify import markdownify as md
from pydantic import BaseModel

from threadslapper.settings import RssFeedToChannel, Settings

settings = Settings()
log = settings.create_logger('RssWatcher')


class EpisodeData(BaseModel):
    number: int
    title: str
    description: str
    image_url: str
    episode_url: str
    channel_title: str
    channel_url: str
    channel_image_url: str
    channel_last_published: str
    tags: list[str]  # this doesn't work, ignore it for now

    def get_description(self, truncate: bool = False):
        """
        Converts an HTML formatted document to markdown, limits text to 2000 in length.

        If truncate=true, it will cut the description at the first double line-return.
        """
        desc = md(self.description)

        if truncate:
            first_line_break = desc.index("\n\n")
            return desc[:first_line_break]
        if len(desc) > 2000:
            desc = f"{desc[:1997]}..."

        return desc

    def get_title(self, prefix: str = "", override_ep_number: bool = False) -> str:
        """
        Appends a prefix to a title to make it clear what feed it comes from,
        if the title of the episode does not contain an episode number, prepend
        the episode number in the RSS feed to the episode title.
        """
        if override_ep_number:
            return self.title.strip()
        if self.title.startswith(f"{self.number}"):
            return f"{prefix} {self.title}".strip()
        return f"{prefix} {self.number}: {self.title}".strip()

    def get_timestamp(self) -> datetime:
        """
        Attempt to convert a time format to a datetime object.
        """
        observed_datetime_formats = ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"]
        for dt_fmt in observed_datetime_formats:
            try:
                dt = datetime.strptime(self.channel_last_published, dt_fmt)
                return dt
            except:
                pass
        return datetime.now()


class RssWatcher(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.feeds = settings.get_channels_list()

        log.info(f'Beginning first time check of RSS feed... {", ".join([feed.title for feed in self.feeds])}')
        if settings.startup_latest_episode_check:
            for feed in self.feeds:
                if (latest_episode := self.check_rss(rss=feed)) is not None:
                    log.info(f'{feed.title}: Latest episode checked on bot power on: {latest_episode.number}.')
                else:
                    raise RuntimeError(f"{feed.title}: No episode data found! Please check RSS Feed URL")

    def cog_unload(self):
        self.check_rss_feed.cancel()

    def get_embed(self, feed: RssFeedToChannel, latest_episode: EpisodeData, truncate: bool = False) -> Embed:
        """
        Construct a cool Embed object. Much better looking than just putting text in.
        """
        embed = Embed(
            title=latest_episode.get_title(prefix=feed.title_prefix, override_ep_number=feed.override_episode_numbers),
            description=latest_episode.get_description(truncate=truncate),
            color=Color.from_rgb(*feed.get_color_theme()),
            url=latest_episode.episode_url,
            timestamp=latest_episode.get_timestamp(),
        )
        embed.set_footer(text=f"Tags: {', '.join(latest_episode.tags)}")
        # embed.set_thumbnail(url=latest_episode.channel_image_url)
        embed.set_author(name=latest_episode.channel_title, icon_url=latest_episode.channel_image_url)
        embed.set_image(url=latest_episode.image_url)

        return embed

    def _get_latest_episode_data(self, rss: RssFeedToChannel) -> EpisodeData:
        """Gets the data for the latest episode"""
        data = feedparser.parse(rss.rss_feed)

        channel_info = data.feed
        latest_episode = data.entries[0]

        latest_ep_id = latest_episode.get(rss.rss_episode_key, 0)
        if rss.override_episode_numbers:
            latest_ep_id = len(data.entries)

        return_data = EpisodeData(
            number=latest_ep_id,
            title=latest_episode.get(rss.rss_title_key, "None"),
            episode_url=latest_episode.get(rss.rss_episode_url_key, "None"),
            description=latest_episode.get(rss.rss_description_key, "None"),
            image_url=latest_episode.get(rss.rss_image_key, {}).get('href', ''),
            tags=[tag.term for tag in latest_episode.get(rss.rss_tag_key, [])],
            channel_url=channel_info.get(rss.rss_channel_url_key, ''),
            channel_image_url=channel_info.get(rss.rss_channel_image_key, {}).get('href', ''),
            channel_last_published=channel_info.get(rss.rss_channel_last_published_key, ''),
            channel_title=channel_info.get(rss.rss_channel_title_key, ''),
        )

        return return_data

    async def add_text_thread(
        self,
        channel: TextChannel,
        title: str,
        # img: File | None,
        feed: RssFeedToChannel,
        latest_episode: EpisodeData,
    ) -> Thread | None:
        """If the channel is a regular text channel, spawn a thread"""
        if feed.override_episode_check or not title in [thread.name for thread in channel.threads]:
            message = await channel.send(
                content=latest_episode.get_title(), embed=self.get_embed(feed, latest_episode), suppress=False
            )

            new_thread = await channel.create_thread(
                message=message,
                name=title,
                type=ChannelType.public_thread,
                reason=f"{feed.title}: New Episode ({latest_episode.number}) detected, creating thread: {title}",
            )
            await new_thread.join()
            if (first_msg_in_thread := new_thread.starting_message) is not None:
                await first_msg_in_thread.pin()
            await new_thread.send(content=":thread: :clap:")

            log.info(f"{feed.title}: Thread '{title}' created!")
            return new_thread
        else:
            log.info(f"{feed.title}: Thread '{title}' already exists, returning thread object.")
            threads = [thread for thread in channel.threads if thread.name == title]
            if len(threads) == 1:
                return threads[0]

        return None

    async def add_forum_thread(
        self,
        channel: ForumChannel,
        title: str,
        # img: File | None,
        feed: RssFeedToChannel,
        latest_episode: EpisodeData,
    ) -> Thread | None:
        """If the channel is a Forum, spawn a post (that is actually a thread)"""
        if feed.override_episode_check or not title in [thread.name for thread in channel.threads]:
            new_thread = await channel.create_thread(
                name=title,
                embed=self.get_embed(feed, latest_episode),
                reason=f"{feed.title}: New Episode ({latest_episode.number}) detected, creating thread: {title}",
            )
            await new_thread.join()
            if (message := new_thread.starting_message) is not None:
                # if img:
                #     # Annoyingly I can't attach an image or remove embedded links on thread creation
                #     await message.edit(file=img, suppress=True)
                await message.publish()
            if (first_msg_in_thread := new_thread.starting_message) is not None:
                await first_msg_in_thread.pin()
                await new_thread.send(content=":thread: :clap:", reference=first_msg_in_thread)

            log.info(f"{feed.title}: Channel '{title}' created!")
            return new_thread
        else:
            log.info(f"{feed.title}: Thread '{title}' already exists, returning thread object.")
            threads = [thread for thread in channel.threads if thread.name == title]
            if len(threads) == 1:
                return threads[0]

        return None

    async def create_announcement(
        self,
        feed: RssFeedToChannel,
        latest_episode: EpisodeData,
        announcement: str,
        message: Thread,
    ) -> None:
        """
        Post an announcement with a truncated Embed object as well as a link to the thread.
        """
        if not feed.announce_channel_id:
            return None

        if (announcement_channel := self.bot.get_channel(feed.announce_channel_id)) is not None:
            if isinstance(announcement_channel, TextChannel):
                announce_message = f":thread: :clap:\n# {announcement}\n\n# Discuss here! {message.jump_url}\n\n"
                if (last_announcement_id := announcement_channel.last_message_id) is not None:
                    last_announcement_message = await announcement_channel.fetch_message(last_announcement_id)
                    if announce_message != last_announcement_message.content:
                        log.info(f"{feed.title}: Sending announcement message to {announcement_channel.name}")
                        _announcement = await announcement_channel.send(
                            content=announce_message, embed=self.get_embed(feed, latest_episode, truncate=True)
                        )
                        # await _announcement.publish()
                    else:
                        log.info(f"{feed.title}: Announcement message already exists, skipping.")
                else:
                    log.info(f"{feed.title}: Sending announcement message to {announcement_channel.name}")
                    _announcement = await announcement_channel.send(
                        content=announce_message, embed=self.get_embed(feed, latest_episode, truncate=True)
                    )
                    # await _announcement.publish()

    def check_rss(self, rss: RssFeedToChannel, episode_number_override: int | None = None) -> EpisodeData | None:
        """
        If the latest episode is newer than the currently stored episode,
        return new episode
        """
        current_episode = episode_number_override or rss.current_episode

        latest_episode = self._get_latest_episode_data(rss)

        if latest_episode.number > current_episode:
            rss.current_episode = latest_episode.number
            return latest_episode
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
                if (latest_episode := self.check_rss(rss=feed)) is not None:
                    log.info(f"{feed.title}: New episode found: {latest_episode.number}")

                    channel = self.bot.get_channel(feed.channel_id)
                    # img = None
                    thread = None
                    # if latest_episode.image:
                    #     img = File(fp=BytesIO(latest_episode.image), filename="thumbnail.png")
                    title = latest_episode.get_title(feed.title_prefix, feed.override_episode_prepend_title)

                    if isinstance(channel, TextChannel):
                        thread = await self.add_text_thread(
                            channel=channel,
                            title=title,
                            # img=img,
                            feed=feed,
                            latest_episode=latest_episode,
                        )

                    elif isinstance(channel, ForumChannel):
                        # If the channel is a Forum, spawn a post (that is actually a thread)
                        thread = await self.add_forum_thread(
                            channel=channel,
                            title=title,
                            # img=img,
                            feed=feed,
                            latest_episode=latest_episode,
                        )

                    if thread:
                        await self.create_announcement(
                            feed=feed, latest_episode=latest_episode, announcement=title, message=thread
                        )

                        # Add subscribers belonging to $ROLE to thread
                        if (role := feed.subscriber_role_id) is not None:
                            if members := thread.guild.get_role(role):
                                for member in members.members:
                                    await thread.add_user(member)

                else:
                    log.info(f'{feed.title}: No updates.')
            except Exception as e:
                log.error(e)


def setup(bot: Bot):
    rsswatcher = RssWatcher(bot)
    bot.add_cog(rsswatcher)
