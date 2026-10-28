# DocuForge

A local, Python-powered AI documentation generator. Paste source or upload code files, pick a free OpenRouter model, and export the generated Markdown.

## Run locally

1. Use Python 3.10+.
2. Install dependencies: `python -m pip install -r requirements.txt`
3. Start the app: `python app.py`
4. Open http://127.0.0.1:5000
5. Paste an OpenRouter API key in the app, or set `OPENROUTER_API_KEY` before starting it.

Get a key at [openrouter.ai/keys](https://openrouter.ai/keys). The app only allows model IDs ending in `:free`; free model availability and rate limits are controlled by OpenRouter. Keys entered in the form are sent to this local server only for the generation request and are not stored.

Uploads are processed in memory, limited to 20 files and 2 MB HTTP request size, with a 100 KB per-file and 350 KB combined-source limit. Source is sent to OpenRouter for generation; avoid submitting secrets.
