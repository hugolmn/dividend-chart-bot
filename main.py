import datetime
import random
import yfinance as yf
import tweepy
import altair as alt
import os
import pandas as pd
from utils import generate_dividend_chart

alt.data_transformers.disable_max_rows()

def dividend_chart_reply_request(api, tweet):
    params = tweet.full_text.split('@DividendChart')[-1].strip().split()
    try:
        assert len(params) == 2, 'Wrong number of parameters.'
        ticker, period = params
        ticker = ticker.split('$')[-1]
        chart = generate_dividend_chart(ticker, period)
        chart.save('chart.png')

        media = api.media_upload('chart.png')

        api.update_status(
            status=f"Here is your chart @{tweet.author.screen_name}! Ticker: ${ticker}. Period: {period}.",
            # filename='chart.png',
            media_ids=[media.media_id],
            in_reply_to_status_id=tweet.id,
            auto_populate_reply_metadata=True
        )
    except Exception as e: 
        print(e)

def reply_to_tweets(api):
    latest_fav = api.get_favorites()[0].id

    for tweet in api.mentions_timeline(since_id=latest_fav, tweet_mode='extended'):
        if not tweet.favorited:
            print(f'Processing tweet: {tweet.full_text}')
            dividend_chart_reply_request(api, tweet)
            api.create_favorite(tweet.id)


def dividend_chart_reply_author(api, tweet, ticker, period):
    # Generate chart
    chart = generate_dividend_chart(ticker, period)
    # Save it
    chart.save('chart.png')
    # Upload chart
    media = api.media_upload('chart.png')
    # Tweet it
    api.update_status(
        status=f"Ticker: ${ticker}. Period: {period}.",
        media_ids=[media.media_id],
        in_reply_to_status_id=tweet.id,
        auto_populate_reply_metadata=True
    )

def dividend_chart_achievers(api, period):
    # https://www.invesco.com/us/financial-products/etfs/holdings?audienceType=Investor&ticker=PFM
    # Get random stock
    stock = pd.read_csv(os.path.join('data', 'dividend_achievers.csv')).sample(1)
    ticker = stock['Holding Ticker'].str.strip().iloc[0]
    name = stock['Name'].str.strip().iloc[0]

    # Generate chart
    chart = generate_dividend_chart(ticker, period)
    # Save it
    chart.save('chart.png')
    # Upload chart
    media = api.media_upload('chart.png')
    # Get stock info
    info = yf.Ticker(ticker).info
    stock_details = [
        'Dividend Aristocrats and Achievers',
        f"Name: {name}",
        f"Ticker: ${ticker}. Period: {period}.",
        f"Sector: {info['sector']}",
        f"MarketCap: ${info['marketCap']/1e9:.1f}B",
        f"P/E trailing/fwd: {info['trailingPE']:.1f}/{info['forwardPE']:.1f}"
    ]
    # Tweet it
    api.update_status(
        # status=f"Dividend Aristocrats and Achievers\nName: {name}.\nTicker: ${ticker}. Period: {period}.\nMarket cap: ${info['marketCap']/1e9:.1f}B",
        status='\n'.join(stock_details),
        media_ids=[media.media_id],
    )

def get_tweets_from_list(api):
    # Get tweets from list timeline
    tweets = api.list_timeline(
        list_id="1585331746828173340",
        count=200,
        include_rts=False
    )
    # Get previously posted tweets
    previous_tweets = api.user_timeline(
        count=int(api.get_list(list_id='1585331746828173340').member_count / 2)
    )
    # Get list of user ids replied to in the past 30 tweets
    previous_tweets_user_ids = {t.in_reply_to_user_id for t in previous_tweets}

    # Filter tweets and shuffle
    tweets = [
        t 
        for t in tweets 
        if (
            t.author.id not in previous_tweets_user_ids
            and t.entities['symbols']
            and not t.favorited
        )
    ]
    random.shuffle(tweets)
    return tweets

def react_to_authors(api):
    reacted = False
    period = '10y'
    tweets = get_tweets_from_list(api)

    for tweet in tweets:
        try:
            tweet.favorite()
        except:
            continue
        
        # Get list of tickers in tweet
        tickers = [s['text'] for s in tweet.entities['symbols']]
        print('Tickers for tweet:')
        print(tweet.text)
        print(f'{tickers}')
        # Iterate over randomly over tickers
        while len(tickers):
            # Fetch historical data
            ticker = random.choice(tickers)
            print(f'Getting data for {ticker}')
            past_year = yf.Ticker(ticker).history('1y', interval='3mo', auto_adjust=False)
            
            # If ticker has distributed dividends in the past year, exit loop and generate chart
            if len(past_year[past_year.Dividends > 0]) > 0:
                try:
                    print(f'Attempting to make chart for ticker: {ticker}')
                    dividend_chart_reply_author(api, tweet, ticker, period)
                    print('Succeded!')
                    reacted = True
                    break
                except:
                    pass
            # Else remove it from the ticker list
            tickers.remove(ticker)

        # If a ticker distributing dividends has been found
        if reacted:
            break

   
if __name__ == '__main__':
    auth = tweepy.OAuth1UserHandler(
        consumer_key=os.environ['api_key'],
        consumer_secret=os.environ['api_secret'],
        access_token=os.environ['access_token'],
        access_token_secret=os.environ['access_token_secret']
    )
    api = tweepy.API(auth, wait_on_rate_limit=True)

    reply_to_tweets(api)
    react_to_authors(api)

    if (datetime.datetime.now().minute < 30) and (datetime.datetime.now().hour % 2 == 0):
            dividend_chart_achievers(api, '15y')
