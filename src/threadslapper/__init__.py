from .discordbot import bot, settings

bot.run(settings.token.get_secret_value())
