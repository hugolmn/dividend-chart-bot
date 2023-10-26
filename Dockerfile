FROM python:3.9

RUN apt-get -y update

# Install font
RUN apt-get install -y fonts-lato

# # Create Workdir
WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# Install requirements
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copy pythjon scripts
COPY utils.py utils.py
COPY main.py main.py

# Copy credentials for gsheets
COPY sheets-api-credentials.json sheets-api-credentials.json
# Backup ticker list
COPY ticker_list.csv ticker_list.csv

# # Copy local code to the container image.
# COPY . .

CMD python main.py