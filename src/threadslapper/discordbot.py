from discord import Bot, Intents
from discord.ext import commands

from .__about__ import __version__
from .settings import Settings

settings = Settings()

log = settings.create_logger('discordbot')

cogs_list = [
    'RssWatcher',
]

bot = Bot(intents=Intents(members=True, guilds=True, message_content=True, messages=True, guild_messages=True))
for cog in cogs_list:
    bot.load_extension(f'cogs.{cog}')


@bot.event
async def on_ready():
    log.info(
        "\n".join(
            [
                "\n",
                "=" * 80,
                f"\tBot starting. Version {__version__}",
                "=" * 80,
            ]
        )
    )

    try:
        rsswatcher = bot.get_cog('RssWatcher')
        if rsswatcher:
            rsswatcher.check_rss_feed.start()
        else:
            raise RuntimeError("RssWatcher could not be loaded!")
    except Exception as e:
        log.error(e)
        raise e
