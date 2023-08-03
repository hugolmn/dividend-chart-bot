import datetime
import random
import yfinance as yf
import tweepy
import altair as alt
import os
import pandas as pd
import gspread
from utils import generate_dividend_chart, generate_tweet_ticker_details

alt.data_transformers.disable_max_rows()

def dividend_chart_reply_request(api: tweepy.API, tweet: tweepy.models.Status):
    """
    Reply to a bot request: 
    - extract the ticker and period
    - generate dividend chart
    - create a response tweet with generated chart
    
    Parameters:
    ----------
    api: tweepy.API
        API object to publish tweets
    tweet: tweepy.models.Status
        Tweet to be replied to

    Note:
    ------
    Requires update to API v2.
    """
    params = tweet.full_text.split('@DividendChart')[-1].strip().split()
    try:
        assert len(params) == 2, 'Wrong number of parameters.'
        # if len(params) != 2:
        #     ticker = params[0]
        #     period = '15y'
        # else:
        ticker, period = params
        ticker = ticker.split('$')[-1]
        chart = generate_dividend_chart(ticker, period)
        chart.save('chart.png')

        media = api.media_upload('chart.png')

        # Get stock info
        info = yf.Ticker(ticker).info
        try:
            details = generate_tweet_ticker_details(info)
        except:
            if ticker[0] != '$':
                ticker = '$' + ticker
            details = [ticker]

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

def reply_to_tweets(api: tweepy.API):
    """
    Check mentions since most recent fav and generate dividend charts.
    Mentions are "fav" to indicated that they have already been processed.

    Parameters:
    ----------
    api: tweepy.API
        API object to publish tweets

    Note:
    ------
    Requires update to API v2.
    """
    # Get id of the most recent favorited tweet
    latest_fav = api.get_favorites()[0].id

    # Iterate over recent mentions
    for tweet in api.mentions_timeline(since_id=latest_fav, tweet_mode='extended'):
        if not tweet.favorited:
            print(f'Processing tweet: {tweet.full_text}')
            # Generate dividend chart
            dividend_chart_reply_request(api, tweet)
            # Fav tweet to indicate that processing is done
            api.create_favorite(tweet.id)

def random_dividend_chart(api_v1: tweepy.API, api_v2: tweepy.Client, period: str):
    """
    Select a random ticker and publish dividend chart on twitter. 
    
    Parameters:
    ----------
    api_v1: tweepy.API
        API object to upload media
    api_v2: tweepy.Client
        API client to publish tweets
    period: str
        Time period for generated charts

    Note:
    ------
    Already updated for API v2.
    """
    # Get random stock
    try:
        gc = gspread.service_account(filename=os.path.join('data', 'sheets-api-credentials.json'))
        sheet = gc.open_by_key('1WLR9XICmKZi0QHneZck8yWNVatwssSEv1Qs_oOCVGRg')
        worksheet = sheet.worksheet('Stocks')
        tickers = pd.DataFrame(worksheet.get_all_records())
        stock = tickers.sample(1)
    except Exception as e:
        print(e)
        print('Using ticker list')
        stock = pd.read_csv(os.path.join('data', 'ticker_list.csv')).sample(1)

    ticker = stock['Ticker'].str.strip().iloc[0]

    # Get stock info
    info = yf.Ticker(ticker).info

    currency_symbol = '$'
    if currency := info.get('currency'):
        if currency == 'EUR':
            currency_symbol = '€'
        elif currency == 'GBP':
            currency_symbol = '£'
        elif currency == 'CHF':
            currency_symbol = 'CHF'
    try:
        details = generate_tweet_ticker_details(info, currency_symbol)
    except:
        if ticker[0] != '$':
            ticker = '$' + ticker
        details = [ticker]

    # Generate chart
    chart = generate_dividend_chart(ticker, period, currency_symbol)
    # Save it
    chart.save('chart.png')
    # Upload chart
    media = api_v1.media_upload('chart.png')

    # Tweet it
    api_v2.create_tweet(
        text='\n'.join(details),
        media_ids=[media.media_id],
    )

def dividend_chart_reply_author(api: tweepy.API, tweet: tweepy.models.Status, ticker: str, period: str):
    """
    Generate a chart and publish it as a response to someone else's tweet.

    Parameters:
    ----------
    api: tweepy.API
        API object to publish tweets
    tweet: tweepy.models.Status
        Tweet to react to
    ticker: str
        Ticker to generate chart for
    period: str
        Time period for generated chart

    Note:
    ------
    Requires update to API v2.
    """
    # Generate chart
    chart = generate_dividend_chart(ticker, period)
    # Save it
    chart.save('chart.png')
    # Upload chart
    media = api.media_upload('chart.png')
    # Get ticker details
    info = yf.Ticker(ticker).info
    try:
        details = generate_tweet_ticker_details(info)
    except:
        if ticker[0] != '$':
            ticker = '$' + ticker
        details = [ticker]
    # Tweet it
    api.update_status(
        # status=f"Ticker: ${ticker}. Period: {period}.",
        status='\n'.join(details),
        media_ids=[media.media_id],
        in_reply_to_status_id=tweet.id,
        auto_populate_reply_metadata=True
    )

def get_tweets_from_list(api: tweepy.Client) -> list:
    """
    Collect recent tweets from a specific twitter list, for the past 24h.
    Filter out authors recently replied to (past 60 posts), replies to other tweets.
    Sort output by follower count.

    Parameters:
    ----------
    api: tweepy.API
        API object to publish tweets
   
    Returns:
    -------
    list of tweets.

    Note:
    ------
    Requires update to API v2.
    """
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
        count=60,
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

def react_to_authors(api: tweepy.API):
    """
    Create a tweet as a response to a random tweet for a specific twitter list.
    Tweet replied to has to mention tickers of dividend stocks.

    Parameters:
    ----------
    api: tweepy.API
        API object to publish tweets

    Note:
    ------
    Requires update to API v2.
    """
    reacted = False
    period = '15y'
    tweets = get_tweets_from_list(api)

    for tweet in tweets:
        # Fails if already favorited
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

def publish_ranking(api: tweepy.API):
    """
    Generate and publish a ranking of most active users of the @DividendChart bot.
    Counts mentions from the past 4 weeks
    
    Parameters:
    ----------
    api: tweepy.API
        API object to publish tweets
   
    Note:
    ------
    Requires update to API v2.
    """
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

    # Keep past 4 weeks
    mentions = mentions[mentions.created_at >= mentions.created_at.max() - pd.Timedelta('4W')]

    mentions = mentions.loc[~mentions['user.screen_name'].isin(['DividendChart', 'hugo_le_moine_']), ['text', 'user.screen_name']]
    mentions['text'] = mentions.text.str.split('@DividendChart').str[-1].str.split()
    mentions = mentions[mentions.text.str.len() == 2]
    mentions = mentions.assign(ticker=mentions.text.str[0].str.strip('$').str.split('.').str[0].str.upper())
    mentions = mentions.drop(columns=['text'])

    ranking = mentions['user.screen_name'].value_counts().to_frame().reset_index()
    ranking.columns = ['user', 'count']
    ranking['rank'] = ranking['count'].rank(ascending=False, method='dense')
    # ranking['cum_len'] = ranking['user'].str.len().add(1).cumsum()
    ranking = ranking.iloc[:10]
    # ranking = ranking[ranking.cum_len <= (200)]

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
    api_v1 = tweepy.API(auth, wait_on_rate_limit=True)

    api_v2 = tweepy.Client(
        consumer_key=os.environ['api_key'],
        consumer_secret=os.environ['api_secret'],
        access_token=os.environ['access_token'],
        access_token_secret=os.environ['access_token_secret']
    )

    # reply_to_tweets(api)
    
    # Post dividend chart for a random dividend achiever every 2 hours
    # if (datetime.datetime.now().hour in range(6, 23, 1)):
    random_dividend_chart(api_v1, api_v2, '20y')

    # if (datetime.datetime.now().minute < 30) and (datetime.datetime.now().hour in range(9, 22)):
        # react_to_authors(api)

    # Post ranking every sunday at 6pm
    # if (datetime.datetime.now().weekday() == 6) and (datetime.datetime.now().hour == 18) and (datetime.datetime.now().minute < 30):
        # publish_ranking(api)
