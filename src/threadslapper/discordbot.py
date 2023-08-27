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
            rsswatcher.check_rss_feed.start()
        else:
            raise RuntimeError("RssWatcher could not be loaded!")
    except Exception as e:
        log.error(e)
        raise e
