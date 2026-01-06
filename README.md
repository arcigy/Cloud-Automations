# ArciGy Cloud Automations

This repository contains the backend services and automation scripts for ArciGy projects, including the Retell AI Call Agent and the Arcigy website backend.

## Structure

- `/Retell_call_agent`: FastAPI backend for managing AI call agents via Retell AI.
- `/Arcigy_website`: Backend and automation for the main website and booking systems.

## Deployment

To deploy the Retell Call Agent to Railway:

1. Connect this repository to a New Project in [Railway.app](https://railway.app).
2. Set the `ROOT_DIRECTORY` or the start command to:
   `uvicorn Retell_call_agent.main:app --host 0.0.0.0 --port ${PORT:-8002}`
3. Add your environment variables (like `RETELL_API_KEY`) in the Railway Dashboard.
