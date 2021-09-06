from datetime import datetime

import tweepy
import os
from tweepy import OAuthHandler
import json
import wget
import argparse
import configparser


def parse_arguments():
    parser = argparse.ArgumentParser(description='Download pictures from Twitter.')
    group = parser.add_mutually_exclusive_group(required=True)
    parser.add_argument('--config', type=str, default='./config.cfg', help='Path to the configuration file')
    group.add_argument('--username', type=str,
                       help='The twitter screen name from the account we want to retrieve all the pictures')
    group.add_argument('--hashtag', type=str, help='The twitter tag we want to retrieve all the pictures. ')
    parser.add_argument('--num', type=int, default=100, help='Maximum number of tweets to be returned.')
    parser.add_argument('--retweets', default=False, action='store_true', help='Include retweets')
    parser.add_argument('--replies', default=False, action='store_true', help='Include replies')
    parser.add_argument('--output', default='pictures/', type=str, help='folder where the pictures will be stored')
    parser.add_argument('--timeline', default='2021-04-03 00:00:00', type=str, help='first tweet time(desc)')

    args = parser.parse_args()
    return args


def parse_config(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    return config


def parse(cls, api, raw):
    status = cls.first_parse(api, raw)
    setattr(status, 'json', json.dumps(raw))
    return status


def init_tweepy():
    # Status() is the data model for a tweet
    tweepy.models.Status.first_parse = tweepy.models.Status.parse
    tweepy.models.Status.parse = parse
    # User() is the data model for a user profile
    tweepy.models.User.first_parse = tweepy.models.User.parse
    tweepy.models.User.parse = parse


def authorise_twitter_api(config):
    auth = OAuthHandler(config['DEFAULT']['consumer_key'], config['DEFAULT']['consumer_secret'])
    auth.set_access_token(config['DEFAULT']['access_token'], config['DEFAULT']['access_secret'])
    return auth


# It returns [] if the tweet doesn't have any media
def tweet_media_urls(tweet_status):
    # At least one image
    if 'media' in tweet_status.entities:
        # Grabbing all pictures
        media = tweet_status.extended_entities['media']
        return [f"{item['media_url']}?format=jpg&name=large" for item in media]
    else:
        return []


def create_folder(output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)


def download_images(status, num_tweets, output_folder, timeline):
    create_folder(output_folder)
    downloaded = 0

    error_url_map = {}

    for tweet_status in status:
        if downloaded >= num_tweets:
            break

        for count, media_url in enumerate(tweet_media_urls(tweet_status)):
            # Only download if there is not a picture with the same name in the folder already
            threshold = datetime.strptime(timeline, "%Y-%m-%d %H:%M:%S")
            created = tweet_status.created_at.strftime('%Y-%m-%d %H.%M.%S')
            file_name = "{}_{}.jpg".format(created, count + 1)
            if threshold < tweet_status.created_at:
                print("curr tweet:" + file_name + ",skip:" + media_url)
                continue
            if not os.path.exists(os.path.join(output_folder, file_name)):
                print(media_url)
                print(output_folder + file_name)
                # TODO: Figure out how to include ':orig' at the end in a way that works with wget to get the
                # full size resolution
                try:
                    wget.download(media_url, out=output_folder + file_name)
                except Exception as e:
                    error_url_map[file_name] = media_url
                    print("error when wget " + created + ",url:" + media_url)
                    print(e)
                    pass
                downloaded += 1
    print("download completed")
    print(error_url_map)


def download_images_by_user(api, username, retweets, replies, num_tweets, output_folder, timeline):
    status = tweepy.Cursor(api.user_timeline, screen_name=username, include_rts=retweets, exclude_replies=replies,
                           tweet_mode='extended').items()
    download_images(status, num_tweets, "pictures/" + username + "/", timeline)


def download_images_by_tag(api, tag, retweets, replies, num_tweets, output_folder, timeline):
    status = tweepy.Cursor(api.search, '#' + tag, include_rts=retweets, exclude_replies=replies,
                           tweet_mode='extended').items()
    download_images(status, num_tweets, "pictures/" + "#" + tag + "/", timeline)


def main():
    arguments = parse_arguments()
    username = arguments.username
    hashtag = arguments.hashtag
    retweets = arguments.retweets
    replies = arguments.replies
    num_tweets = arguments.num
    output_folder = arguments.output
    config_path = arguments.config
    timeline = arguments.timeline

    config = parse_config(config_path)
    auth = authorise_twitter_api(config)
    api = tweepy.API(auth, wait_on_rate_limit=True)

    if hashtag:
        download_images_by_tag(api, hashtag, retweets, replies, num_tweets, output_folder, timeline)
    else:
        download_images_by_user(api, username, retweets, replies, num_tweets, output_folder, timeline)


if __name__ == '__main__':
    main()
