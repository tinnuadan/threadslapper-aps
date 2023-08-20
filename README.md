# Threadslapper

Monitors the [Brad & Will Made a Tech Pod](https://feeds.simplecast.com/qKIEAGzn) RSS feed for new episodes. If a new episode is posted it will download the thumbnail and create a new thread in the `#this-weeks-episode` forum.

## Setting up bot

1. Create a new bot in <https://discord.com/developers/applications>
2. In the new bot's settings on the developer portal, go to the `Bot` tab, and get a token (click `Reset Token`), and save this to a file on your local machine.
3. In the new bot's `Oauth2` tab, click `URL Generator` and create a new URL with the `Bot` scopes:
    - `Read Messages/View Channels`
    - `Send Messages`, `Create Public Threads`
    - `Create Private Threads`
    - `Send Messages in Threads`
    - `Manage Threads`.
4. Open the generated URL and add the bot to the desired server (`Brad & Will Made a Tech Pod`).

## Setting up docker container

Create a `.env` file mapping to all variables defined in `docker-compose.yml`, then execute `docker compose up -d --build`.

An example would be:

```properties
THREADSLAPPER_TOKEN=BOT_TOKEN_FROM_DISCORD
THREADSLAPPER_FORUM_CHANNEL_NAME=this-weeks-episode
THREADSLAPPER_RSS_FEED=https://feeds.simplecast.com/qKIEAGzn
THREADSLAPPER_CHECK_INTERVAL_MIN=5
```
