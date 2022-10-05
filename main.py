import tweepy
import altair as alt
import os
import itertools
from utils import generate_dividend_chart

alt.data_transformers.disable_max_rows()

def process_dividend_bot_request(api, tweet):
    params = tweet.full_text.split('@DividendChart')[-1].strip().split()
    try:
        assert len(params) == 2, 'Wrong number of parameters.'
        ticker, period = params
        chart = generate_dividend_chart(ticker, period)
        chart.save('chart.png')

        api.update_status_with_media(
            status=f"Here is your chart @{tweet.author.screen_name}! Ticker: {ticker}. Period: {period}.",
            filename='chart.png',
            in_reply_to_status_id=tweet.id
        )
    except Exception as e: 
        print(e)
        # api.update_status(
        #     status=f"Sorry @{tweet.author.screen_name}, there is something wrong with your query. Please try again!",
        #     in_reply_to_status_id=tweet.id,
        # )

def reply_to_tweets(api):
    latest_fav = api.get_favorites()[0].id

    for tweet in api.mentions_timeline(since_id=latest_fav, tweet_mode='extended'):
        if not tweet.favorited:
            print(f'Processing tweet: {tweet.full_text}')
            process_dividend_bot_request(api, tweet)
            api.create_favorite(tweet.id)

def react_to_tickers(api):
    tickers = [
        'SPG',
        'O',
        'WPC',
        'ARE',
        'DLR',
        'NNN',
        'IIPR',
        'PLD',
        'ADC',
        'VICI',
        'BAM',
        'MPW',
        'FRT'
    ]
    accounts_to_follow = [
        'HighDividends',
        'Dividend_Dollar',
        'rbradthomas',
        'CalebGregory304'
    ]

    period = '20y'
    for ticker, author in itertools.product(tickers, accounts_to_follow):
        # Collect recent tweets
        tweets = api.search_tweets(
            f'${ticker} from:{author}',
            result_type='recent',
            count=10,
            tweet_mode='extended',
            lang='en'
        )
        # Iterate over each tweet
        for tweet in tweets:
            # Ignore if already favorited
            if not tweet.favorited and (tweet.author.followers_count < 1000) and (len(tweet.entities['symbols']) == 1):
                # Generate chart
                chart = generate_dividend_chart(ticker, period)
                # Save it
                chart.save('chart.png')
                # Tweet it
                # api.update_status_with_media(
                #     status=f"@{tweet.author.screen_name}\nTicker: {ticker}. Period: {period}.",
                #     filename='chart.png',
                #     in_reply_to_status_id=tweet.id
                # )
                print(f'Replying to tweet: {tweet.full_text}')
                # Fav tweet replied to
                # api.create_favorite(tweet.id)


if __name__ == '__main__':
    auth = tweepy.OAuth1UserHandler(
        consumer_key=os.environ['api_key'],
        consumer_secret=os.environ['api_secret'],
        access_token=os.environ['access_token'],
        access_token_secret=os.environ['access_token_secret']
    )
    api = tweepy.API(auth, wait_on_rate_limit=True)

    reply_to_tweets(api)
    # react_to_tickers(api)