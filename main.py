import tweepy
import altair as alt
import os
from utils import generate_dividend_chart

alt.data_transformers.disable_max_rows()

def process_dividend_bot_request(api, tweet):
    params = tweet.text.split()
    try:
        ticker, period = params[1:]
        chart = generate_dividend_chart(ticker, period)
        chart.save('chart.png')

        api.update_status_with_media(
            status=f"Here is your chart @{tweet.user.screen_name}! Ticker: {ticker}. Period: {period}.",
            filename='chart.png',
            in_reply_to_status_id=tweet.id
        )
    except Exception as e: 
        print(e)
        api.update_status(
            status=f"Sorry @{tweet.user.screen_name}, there is something wrong with your query. Please try again!",
            in_reply_to_status_id=tweet.id,
        )

if __name__ == '__main__':
    auth = tweepy.OAuth1UserHandler(
        consumer_key=os.environ['api_key'],
        consumer_secret=os.environ['api_secret'],
        access_token=os.environ['access_token'],
        access_token_secret=os.environ['access_token_secret']
    )
    api = tweepy.API(auth)

    latest_fav = api.get_favorites()[0].id

    for tweet in api.mentions_timeline(since_id=latest_fav):
        if not tweet.favorited and tweet.in_reply_to_status_id is None:
            print(f'Processing tweet: {tweet.text}')
            tweet.text
            process_dividend_bot_request(api, tweet)
            api.create_favorite(tweet.id)
