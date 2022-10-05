# Dividend Chart Bot

I have built a [streamlit app](https://hugolmn-finance-tools-finance-tools-qw1pw5.streamlitapp.com/Dividends) with pretty nice looking charts. I wanted to create a Twitter bot that can generate and post them on-demand.

## Architecture
- Container:
    - [`main.py`](/main.py): all the code that needs to run on a schedule.
    - [`utils.py`](/utils.py): utility functions to generate charts.
    - [`Dockerfile`](/Dockerfile): image with chromedriver to run selenium (required to generate altair png exports).
- Build: [Google Cloud Build](https://cloud.google.com/build)
- Image storage: [Google Artifact Registry](https://cloud.google.com/artifact-registry)
- Run: [Google Cloud Run Jobs](https://cloud.google.com/run)
- Scheduling: [Google Cloud Scheduler](https://cloud.google.com/scheduler)

## Diagram
![](/docs/dividend_chart_bot.png)

## Run your own bot
### Pre-requisites
- [Google Cloud account](https://cloud.google.com) set up with a project created in it.
- [Twitter developer account](https://developer.twitter.com) set up with an app already created. You need Consumer and Access tokens/secrets.

### Local development
```bash
git clone https://github.com/hugolmn/dividend-chart-bot.git
cd dividend-chart-bot
```

### Building image using Google Cloud Build
1. Install the gcloud CLI following these [instructions](https://cloud.google.com/sdk)
2. Enable the Artifact Registry API.
3. Create a registry
Now, to create an image and store it into the registry, you can run the following commands from your code workspace:
```bash
gcloud builds submit --tag <YOUR_REGION>-docker.pkg.dev/<YOUR_PROJECT_ID>/<YOUR_REGISTRY>/<YOUR_IMAGE_NAME>:latest
```

### Creating a Cloud Run Job
1. Search "Cloud Run" > Select "Jobs" tab > "Create Job".
2. For "Container image URL": select your registry in "Artifact Registry" > Select your image name > Select your image version
3. If you always want to run on the lastest image version, replace the ending "@sha:******" by ":latest". in the "Container image URL".
4. Select your job name, region, task capacity etc.
5. In the "Variables & Secrets" tab, create the environment variables "api_key", "api_secret", "access_token", "access_token_secret", with the appropriate values from your Twitter developer account. You can also use secrets (free tier is limited to 6 secrets).
6. Create your job.

### Create a Cloud Scheduler
1. Enable the Cloud Scheduler API if needed.
2. Create a job following these [instructions](https://cloud.google.com/run/docs/execute/jobs-on-schedule#using-scheduler).

**Congratulations! Your bot is now all set!**