# Dividend Chart Bot

I have built a [streamlit app](https://hugolmn-finance-tools-finance-tools-qw1pw5.streamlitapp.com/Dividends) with pretty nice looking charts. I wanted to create a Twitter bot that can generate and post them on-demand.

## Architecture
- Container:
    - [`main.py`](/main.py): all the code that needs to run on a schedule.
    - [`Dockerfile`](/Dockerfile): created image with chromedriver to run selenium (required to generate altair png exports).
- Build: [Google Cloud Build](https://cloud.google.com/build)
- Image storage: [Google Artifact Registry](https://cloud.google.com/artifact-registry)
- Run: [Google Cloud Run Jobs](https://cloud.google.com/run)
- Scheduling: [Google Cloud Scheduler](https://cloud.google.com/scheduler)

## Diagram
![](/docs/dividend_chart_bot.png)