# API Keys And Environment Setup

Do not commit provider API keys into this repository.

Use a local `.env` file for development and configure environment variables in the deployment platform for production.

## Required Environment Variables

```bash
ARK_API_KEY=replace_with_byteplus_key
BYTEPLUS_BASE_URL=https://ark.ap-southeast.bytepluses.com/api/v3
SEEDANCE_MODEL=dreamina-seedance-2-0-260128
```

## Optional Environment Variables

```bash
MEDIA_ROOT=./tmp/media
RUNS_ROOT=./tmp/runs
PUBLIC_BASE_URL=http://localhost:8000
```

`PUBLIC_BASE_URL` must be reachable by Seedance if the provider needs to fetch the source recording through a public URL. For local demos, expose the backend with a temporary tunnel and use that public URL.

## BytePlus Docs

- Model list: https://docs.byteplus.com/en/docs/ModelArk/1330310
- Seedance 2.0 tutorials: https://docs.byteplus.com/en/docs/ModelArk/2291680
- General video generation tutorials: https://docs.byteplus.com/en/docs/ModelArk/2298881
- Seedance 2.0 prompt guide: https://docs.byteplus.com/en/docs/ModelArk/2222480
- Create task API: https://docs.byteplus.com/en/docs/ModelArk/1520757
- Query task status API: https://docs.byteplus.com/en/docs/ModelArk/1521309
- Query list API: https://docs.byteplus.com/en/docs/ModelArk/1521675
- Quick start: https://docs.byteplus.com/en/docs/ModelArk/1399008

## Local Setup Checklist

1. Create `.env`.
2. Add `ARK_API_KEY`.
3. Start the backend.
4. Expose backend with a tunnel if Seedance must fetch local videos.
5. Set `PUBLIC_BASE_URL` to the tunnel URL.
6. Run a short test generation before the demo.
