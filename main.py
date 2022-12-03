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

        # Get stock info
        info = yf.Ticker(ticker).info
        if info['quoteType'] == "EQUITY":
            details = [
                f"{info['shortName']} (${ticker}):",
                f"• Sector: {info['sector']}",
                f"• MarketCap: ${info['totalAssets']/1e9:.1f}B",
                f"• P/E trailing/fwd: {info['trailingPE']:.1f}/{info['forwardPE']:.1f}"
            ]
        elif info['quoteType'] == "ETF":
            details = [f"{info['shortName']}:"]

            if holdings := ['$' + holding['symbol'] for holding in info['holdings'][:5] if holding['symbol'] != '']:
                details += [f"• Top holdings: {' '.join(holdings)}"]

            if 'totalAssets' in info and info['totalAssets']:
                details += [f"• AUM: ${info['totalAssets']/1e9:.2f}B"]

            if equity_holdings := info['equityHoldings']:
                if 'priceToEarnings' in equity_holdings and equity_holdings['priceToEarnings']:
                    details += [f"• P/E: {info['equityHoldings']['priceToEarnings']:.1f}"]

        else:
            details = [
                f"Here is your chart @{tweet.author.screen_name}!"
            ]

        api.update_status(
            # status=f"Here is your chart @{tweet.author.screen_name}! Ticker: ${ticker}. Period: {period}.",
            status='\n'.join(details),
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
    list_timeline = api.list_timeline(
        list_id="1585331746828173340",
        count=200,
        include_rts=False, 
    )

    # Init timeline dataframe
    timeline = pd.json_normalize([t._json for t in list_timeline])
    timeline['created_at'] = pd.to_datetime(timeline.created_at)
    timeline['status'] = list_timeline

    while timeline.created_at.min() > timeline.created_at.max() - pd.Timedelta('1D') and len(timeline) < 500:
        # Get oldest tweet it in current timeline dataframe
        oldest_tweet_id = timeline[timeline.created_at == timeline.created_at.min()].iloc[0].id
        # Collect older tweets
        list_timeline = api.list_timeline(
            list_id="1585331746828173340",
            count=200,
            include_rts=False, 
            max_id=oldest_tweet_id
        )

        # Create temporary dataframe with older data
        _timeline = pd.json_normalize([t._json for t in list_timeline])
        _timeline['created_at'] = pd.to_datetime(_timeline.created_at)
        _timeline['status'] = list_timeline

        # Merge dataframes:
        timeline = pd.concat([timeline, _timeline])
        timeline = timeline.drop_duplicates(subset=['id'])

    # Get previously posted tweets
    previous_tweets = api.user_timeline(
        count=30,
    )
    # Get list of user ids replied to in the past 24 tweets
    previous_tweets_user_ids = {t.in_reply_to_user_id for t in previous_tweets}

    timeline = timeline[
        ~timeline['user.id'].isin(previous_tweets_user_ids) # Not recently replied to
        & ~timeline.favorited # No already favorited
        & timeline.in_reply_to_status_id.isna() # Not a reply to another tweet
        & timeline['entities.symbols'].apply(len) != 0 # At least one ticker mentioned
    ]
    timeline = timeline.sort_values(by='user.followers_count', ascending=False) # Sort by number of followers
    filtered_tweets = timeline['status'].tolist()
    return filtered_tweets

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
        random.shuffle(tickers)
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

def publish_ranking(api):
    # Get most recent 200 tweets
    mentions_timeline = api.mentions_timeline(count=200)

    # Init timeline dataframe
    mentions = pd.json_normalize([t._json for t in mentions_timeline])
    mentions['created_at'] = pd.to_datetime(mentions.created_at)

    while mentions.created_at.min() > mentions.created_at.max() - pd.Timedelta('4W'):
        # Get oldest tweet it in current mentions dataframe
        oldest_tweet_id = mentions[mentions.created_at == mentions.created_at.min()].iloc[0].id
        # Collect older tweets
        mentions_timeline = api.mentions_timeline(count=200, max_id=oldest_tweet_id)

        # Create temporary dataframe with older data
        _mentions = pd.json_normalize([t._json for t in mentions_timeline])
        _mentions['created_at'] = pd.to_datetime(_mentions.created_at)

        # Merge dataframes:
        mentions = pd.concat([mentions, _mentions])
        mentions = mentions.drop_duplicates(subset=['id'])

    # Keep past week
    mentions = mentions[mentions.created_at >= mentions.created_at.max() - pd.Timedelta('4W')]

    mentions = mentions.loc[~mentions['user.screen_name'].isin(['DividendChart', 'hugo_le_moine_']), ['text', 'user.screen_name']]
    mentions['text'] = mentions.text.str.split('@DividendChart').str[-1].str.split()
    mentions = mentions[mentions.text.str.len() == 2]
    mentions = mentions.assign(ticker=mentions.text.str[0].str.strip('$').str.split('.').str[0].str.upper())
    mentions = mentions.drop(columns=['text'])

    ranking = mentions['user.screen_name'].value_counts().to_frame().reset_index()
    ranking.columns = ['user', 'count']
    ranking['rank'] = ranking['count'].rank(ascending=False, method='dense')
    ranking = ranking[ranking['rank'] <= 3]

    tweet_most_active_users = [
        'Most active users in the past month:',
        '\n'.join('@' + ranking.user),
        'Thank you all! :)'
    ]

    api.update_status(status='\n'.join(tweet_most_active_users))


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

    # Post dividend chart for a random dividend achiever every 2 hours
    if (datetime.datetime.now().minute < 30) and (datetime.datetime.now().hour % 2 == 0):
            dividend_chart_achievers(api, '15y')

    # Post ranking every sunday at 6pm
    if (datetime.datetime.now().weekday() == 6) and (datetime.datetime.now().hour == 18) and (datetime.datetime.now().minute < 30):
        publish_ranking(api)
