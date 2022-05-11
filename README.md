# actions

This repository hosts different custom actions which are deployed to auroraai -chatbots

## TODO
- Structure components according to good Python structure (PEP?)
- Add code of conduct
- Publish as public repository

## Components

`api.py` - Fetches data from Suomi.fi Finnish Service Catalogue REST API (requires correct API_KEY and CLIENT_ID)
`utils.py` - List of municipalities and their respective codes in Finland
`actions.py` - the actual actions which contain functions available to define in botfront and use in rasa conversations

## Requirements

Create a .env file with the following names and content
```
AURORA_API_ENDPOINT=https://auroraai.astest.suomi.fi/service-recommender/v1/
AURORA_API_KEY=api_key_123
AURORA_API_CLIENT_ID=client_id_xyz
```

For build args find out a good version of rasa-sdk from Dockerhub

## Building
For local environment
```
docker build -t local-actions --build-arg RASA_SDK_IMAGE=rasa/rasa-sdk:2.8.3 .
```
For cloud environment
```
docker build -t cloud-actions -f Dockerfile.production --build-arg RASA_SDK_IMAGE=rasa/rasa-sdk:2.8.3 .
```