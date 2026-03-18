# Deployment and Operations

## Current state

The project currently runs as a local Streamlit app using a local Python virtual environment and an OpenAI API key loaded from `.env`.

This is enough for internal use and rapid iteration but not yet for hosted production.

## Local operation model

### Dependencies
- Python 3.10+
- virtual environment
- requirements from `requirements.txt`
- `.env` containing `OPENAI_API_KEY`

### Launch
```powershell
.\venv\Scripts\Activate.ps1
streamlit run src/app.py
```

### Operational characteristics
- single-user oriented
- local files only
- no authentication
- API key managed locally
- no persistent run history

## Hosted deployment path

### Option 1 — Streamlit hosted internally

Best for fast internal rollout.

Requirements:
- deploy app to Azure App Service, Render, or similar
- store API key in server-side secrets
- restrict access with SSO or basic authentication
- attach file storage only if needed for audit/logging

Pros:
- fastest route to team access
- minimal code changes

Cons:
- Streamlit is not ideal for more complex multi-user workflow later

### Option 2 — API backend + separate frontend

Best for longer-term SaaS or enterprise deployment.

Requirements:
- backend service exposing translation endpoints
- queue for long-running jobs
- frontend app for upload, review, and download
- user accounts, billing, usage tracking

Pros:
- scalable architecture
- cleaner separation between engine and UI

Cons:
- more engineering work up front

## Secrets and config

### Current config
- `.env` in project root
- API key optionally entered in UI sidebar

### Recommended production config
- environment variables only
- no secrets written to disk by the web app
- per-environment config for dev, staging, production

## Observability

Recommended metrics to capture once hosted:
- files translated per day
- segments translated per run
- API token usage by model
- cache hit rate once translation memory exists
- number of failed items
- average run duration by file type

Recommended logs:
- run start/end timestamps
- file type and size
- selected model and target language
- warnings and failures

## Security considerations

- never commit `.env`
- avoid persisting uploaded files unless required
- redact API keys from logs
- consider client-side file deletion after download in hosted mode
- review whether source files contain confidential product or legal content

## Cost operations

Current cost drivers:
- model choice
- file size
- batch size
- repeated strings without translation memory

Cost controls to add:
- cost estimate before execution
- model recommendations per content type
- translation memory / cache
- usage quotas per user in hosted mode

## Release strategy

### Internal release
- ship locally to a small user group
- collect real file samples
- tune prompts and glossary support first

### Pilot release
- host for one or two internal/external teams
- monitor cost and quality
- add review workflow and memory before broadening scope

### Product release
- authentication
- durable job tracking
- stronger testing and support coverage
- billing or internal cost allocation

## Operational next steps

1. add cost estimator
2. add translation memory
3. add structured run logging
4. decide whether the next milestone is internal hosting or new format support
