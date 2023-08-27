# Threadslapper

Monitors multiple RSS feeds for new episodes. If a new episode is posted it will download the thumbnail and create a new thread in a specified discord forum.

## Setting up bot

1. Create a new bot in <https://discord.com/developers/applications>
2. In the new bot's settings on the developer portal, go to the `Bot` tab, and get a token (click `Reset Token`), and save this to a file on your local machine.
3. In the new bot's `Oauth2` tab, click `URL Generator` and create a new URL with the `Bot` scopes:
    - `Read Messages/View Channels`
    - `Send Messages`, `Create Public Threads`
    - `Create Private Threads`
    - `Send Messages in Threads`
    - `Manage Threads`.
4. Open the generated URL and add the bot to the desired server (ex: `Brad & Will Made a Tech Pod`).

## Setting up docker container

Create a `.env` file mapping to all variables defined in `docker-compose.yml`, then execute `docker compose up -d --build`.

An example would be:

```properties
THREADSLAPPER_TOKEN=BOT_TOKEN_FROM_DISCORD
THREADSLAPPER_CHECK_INTERVAL_MIN=5
THREADSLAPPER_POST_LATEST_EPISODE_CHECK=true
THREADSLAPPER_CONFIG_FILE=config.yml
```

## Setting a watch on an RSS Feed

### Single RSS feed

For a single RSS feed, you can specify the following environment variables in the docker-compose file and associated `.env`:

```yaml
THREADSLAPPER_CHANNEL__ENABLED: true|false
THREADSLAPPER_CHANNEL__TITLE: example feed title
THREADSLAPPER_CHANNEL__TITLE_PREFIX: The prefix to attach to forum posts
THREADSLAPPER_CHANNEL__CHANNEL_ID: discord channel ID
THREADSLAPPER_CHANNEL__RSS_FEED: url_to_rss_feed

# If your RSS feed's XML configuration differs from these keys, set them.
THREADSLAPPER_CHANNEL__RSS_EPISODE_KEY: itunes_episode
THREADSLAPPER_CHANNEL__RSS_TITLE_KEY: itunes_title
THREADSLAPPER_CHANNEL__RSS_DESCRIPTION_KEY: subtitle
THREADSLAPPER_CHANNEL__RSS_IMAGE_KEY: image
```

### Multiple RSS feeds

You can load in a yaml file that supports multiple RSS feeds:

> **NOTE:** While the yaml configuration maps 1:1 with the previously defined environment variable names (starting after `__`), the environment variable `TITLE` is one level higher than all other keys

```yaml
---
# title_of_feed:
#   title_prefix: foo
#   enabled: true
#   channel_id: -1
#   rss_url: https://your.url.here
#   # XML metadata here
#   rss_episode_key: itunes_episode
#   rss_title_key: itunes_title
#   rss_description_key: summary
#   rss_image_key: image
techpod:
  enabled: true
  channel_id: 1140732303849570541
  rss_url: https://feeds.simplecast.com/qKIEAGzn
  rss_episode_key: itunes_episode
  rss_title_key: itunes_title
  rss_description_key: summary
  rss_image_key: image
fosspod:
  enabled: false
  title_prefix: FOSSPOD
  channel_id: 1140732303849570541
  rss_url: https://feeds.simplecast.com/5JzYp_Kp
  rss_episode_key: itunes_episode
  rss_title_key: itunes_title
  rss_description_key: summary
  rss_image_key: image
nextlander:
  enabled: false
  channel_id: 849384215983554603
  rss_url: https://www.omnycontent.com/d/playlist/77bedd50-a734-42aa-9c08-ad86013ca0f9/2b6eadde-60d3-45b4-aac8-ae04014687dd/6554b463-2d55-4d17-a6c1-ae04014687f0/podcast.rss
  rss_episode_key: itunes_episode
  rss_title_key: title
  rss_description_key: summary
  rss_image_key: image
```
