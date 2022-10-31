import yfinance as yf
import pandas as pd
import numpy as np
import altair as alt
import seaborn as sns
import datetime
alt.data_transformers.disable_max_rows()

def load_ticker_data(ticker: str, period: str) -> pd.DataFrame:
    """
    Returns stock history from a ticker and a period.

    Parameters:
    ----------
    - ticker: str
        Ticker from yahoo finance
    - period: str
        Period to collect data from (ytd, 1wk, 1m, 6m, 1y, 10y, ..., max)

    Returns:
    -------
    - pd.DataFrame containing stock historical data
    """
    return yf.Ticker(ticker).history(
        period=period,
        auto_adjust=False
    )

def process_dividend_history(history):
    # Get df with dividend distributions
    dividends = history.loc[history.Dividends > 0, 'Dividends'].to_frame()

    # Keep one distribution per month
    dividends['Month'] = dividends.index.to_period('1M')
    dividends = (dividends
        .reset_index()
        .groupby('Month', as_index=False)
        .first()
        .set_index('Date')
        .drop(columns=['Month'])
    )

    # Count distributions per year
    yearly_distributions = dividends.groupby(dividends.index.year).Dividends.count()
    # First and current year do not have all distributions, use next and previous year's numbers
    yearly_distributions.iloc[0] = yearly_distributions.iloc[1]
    yearly_distributions.iloc[-1] = yearly_distributions.iloc[-2]
    # Map values
    dividends['AnnualDividendCount'] = dividends.index.year.map(yearly_distributions)
    dividends['AnnualDividendCount'] = pd.cut(
        dividends.AnnualDividendCount,
        bins=[-np.inf, 0, 1, 2, 3, 4, 8, 12],
        labels=[0, 1, 2, 4, 4, 4, 12],
        ordered=False,
    ).astype(int)

    dividends['SmoothedDividends'] = (dividends
        .Dividends
        .rolling(5, center=True)
        .median()
    )
    # ).bfill().ffill()
    dividends['SmoothedDividends'] = dividends.SmoothedDividends.combine_first(dividends.Dividends)
    # dividends['YearlyDividends'] = dividends.SmoothedDividends * dividends.AnnualDividendCount

    dividends['YearlyDividends']= np.where(
        dividends.AnnualDividendCount <= 3, 
        dividends.index.year.map(dividends.groupby(dividends.index.year).Dividends.sum()),
        dividends.SmoothedDividends * dividends.AnnualDividendCount
    )

    # Get at least one full year
    dividends = dividends.loc[dividends.index > dividends.index[0] + datetime.timedelta(days=365)]

    # Growth in dividends since beginning of timeframe
    dividends['DivGrowth'] = dividends['YearlyDividends'] / dividends['YearlyDividends'].iloc[0] - 1
    dividends = dividends.reset_index()
    
    return dividends

def generate_dividend_chart(ticker, period):
        # Load historical data
    history = load_ticker_data(
        ticker=ticker,
        period=f"{int(period.split('y')[0]) + 1}y" if 'y' in period else period
    )

    dividends = process_dividend_history(history)

    # Merge dividends with price history
    df = pd.merge(
        left=history.reset_index(),
        right=dividends.drop(columns=['Dividends']),
        on='Date',
        how='left'
    ).ffill(limit=300).fillna(0)

    df['Drawdown'] = df.Close / df.Close.cummax() - 1

    # Keep data from first dividend
    index_first_dividend = df[df.YearlyDividends > 0].index[0]
    df = df.loc[index_first_dividend:]

    # Drop where dividends is null
    df = df[df.YearlyDividends.notna()]
    # Calculate dividend yield base on TTM distributions
    df['DividendYield'] = df.YearlyDividends / df.Close

    # Calculate quantiles of dividend yield
    quantiles = df.DividendYield.quantile(q=np.arange(0, 1.1, .1))
    yield_df = pd.DataFrame(df.YearlyDividends.to_numpy()[:, None] / quantiles.to_numpy(), index=df.Date)
    yield_df.columns = [f"{decile * 10}%" for decile in yield_df.columns[::-1]]
    yield_df = yield_df.reset_index()

    # Create color palette and scale for legend
    palette = sns.color_palette("vlag_r", len(quantiles)-1).as_hex()
    scale = alt.Scale(domain=yield_df.columns[1:-1].tolist(), range=palette)

    # Create layers for chart
    def make_layer(yield_df, col1, col2):
        return alt.Chart(yield_df.assign(color=col1)).mark_area().encode(
            x=alt.X(
                'Date:T',
                title='',
                axis=alt.Axis(format='%Y', tickCount='year')
            ),
        ).encode(
            y=alt.Y(
                f"{col1}:Q",
                title='Stock Price',
                axis=alt.Axis(format='$.0f'),
                scale=alt.Scale(zero=False, domain=[df.Close.min()*0.9, df.Close.max()*1.15], clamp=True),
            ),
            y2=alt.Y2(
                f"{col2}:Q",
                title='Stock Price',
            ),
            color=alt.Color(
                f"color:N",
                title='Yield percentile',
                scale=scale,
                legend=alt.Legend(
                    legendX=0,
                    legendY=-30,
                    padding=5,
                    orient='none',
                    direction='horizontal',
                    titleFontSize=22,
                    labelFontSize=20,
                    titleLimit=0,
                    titleOrient='left'
                )
            ),
            opacity=alt.value(0.8)
        )

    layers=[]
    for col1, col2 in zip(yield_df.columns[1:-1], yield_df.columns[2:]):
        layers.append(make_layer(yield_df, col1, col2))

    price = alt.Chart(df).mark_line(color='black').encode(
        x=alt.X(
            'Date:T',
            title='',
            axis=alt.Axis(format='%Y', labels=False, ticks=False, domain=False, tickCount='year'),
        ),
        y=alt.Y('Close:Q', scale=alt.Scale(zero=False))
    )
    layers.append(price)

    yield_chart = price.encode(
        x=alt.X(
            'Date:T',
            title='',
            axis=alt.Axis(format='%Y', labels=False, ticks=False, domain=False, tickCount='year')
        ),
        y=alt.Y(
            'DividendYield:Q',
            axis=alt.Axis(format='.1%'),
            scale=alt.Scale(zero=False)
        )
    )

    drawdown_chart = price.encode(
        x=alt.X(
            'Date:T',
            title='',
            axis=alt.Axis(format='%Y', tickCount='year')
        ),
        y=alt.Y(
            'Drawdown:Q',
            axis=alt.Axis(format='.0%'),
            scale=alt.Scale(zero=False)
        )
    )

    percentile = int((1 - df.DividendYield.rank(pct=True).iloc[-1]) * 100)
    def format_percentile(percentile):
        if (4 <= percentile <= 20) or (percentile % 10 not in [1, 2, 3]):
            return str(percentile) + 'th'
        if percentile % 10 == 1:
            return str(percentile) + 'st'
        if percentile % 10 == 2:
            return str(percentile) + 'nd'
        if percentile % 10 == 3:
            return str(percentile) + 'rd'
            
    percentile_string = format_percentile(percentile)

    price_chart = alt.layer(*layers).properties(
        width=1200,
        height=400,
        title=f"""{ticker} {period} Chart • Price: ${
                    df.iloc[-1].Close:.2f} • Yield: {
                    df.iloc[-1].DividendYield:.2%} ({
                    percentile_string} percentile) • Drawdown: {
                        df.Drawdown.iloc[-1]:.0%}""",
    )
    yield_chart = yield_chart.properties(
        width=1200,
        height=150
    )
    drawdown_chart = drawdown_chart.properties(
        width=1200,
        height=150
    )

    chart = alt.vconcat(
        price_chart,
        yield_chart,
        drawdown_chart,
        spacing=0
    )
    chart = chart.configure(
        background='white',
        font='Lato'
    ).configure_title(
        fontSize=30,
        dy=-15
    ).configure_axisX(
        labelAngle=-35,
        labelFontSize=25
    ).configure_axisY(
        labelFontSize=25,
        titleFontSize=20
    )
    return chart

    chart = alt.layer(
        *layers
    ).properties(
        width=1200,
        height=675
    ).configure(
        background='white',
        font='Lato'
    ).configure_axisY(
        labelFontSize=25,
        titleFontSize=20
    ).configure_axisX(
        labelAngle=-35,
        labelFontSize=25
    )


    # return chart, df