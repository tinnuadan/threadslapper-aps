from discord.ext import commands

from .settings import Settings

settings = Settings()

log = settings.create_logger('discordbot')

cogs_list = [
    'RssWatcher',
]

bot = commands.Bot()
for cog in cogs_list:
    bot.load_extension(f'cogs.{cog}')


@bot.event
async def on_ready():
    log.info("Bot starting.")

    try:
        rsswatcher = bot.get_cog('RssWatcher')
        if rsswatcher:
            log.info('Beginning first time check of RSS feed...')
            new_episode = rsswatcher.check_rss()
            if new_episode:
                log.info(f'Latest episode checked on bot power on: {new_episode.number}.')
                log.info(f'RssWatcher started, checking every {settings.check_interval_min} minutes.')
                rsswatcher.check_rss_feed.start()
            else:
                raise RuntimeError("No episode data found! Please check RSS Feed URL")
        else:
            raise RuntimeError("RssWatcher could not be loaded!")
    except Exception as e:
        log.error(e)
        raise e
