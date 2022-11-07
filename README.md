# actions

This repository hosts different custom actions which are deployed to auroraai -chatbots

## TODO
- Structure components according to good Python structure (PEP?)
- Add code of conduct
- Publish as public repository

## Components

`api.py` - Methods used for connecting bot to the aurora REST API (requires correct API_KEY and CLIENT_ID)
`classification_codes.py` - Dictionaries for codes in koodisto.fi used in aurora-ai api methods.
`utils.py` - Defines fixed slot names, and contains custom action helpers.
`actions.py` - Custom actions used in rasa conversations, and which can be called from botfront.

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