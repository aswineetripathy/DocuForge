from flask import Flask, render_template, request, jsonify, send_file
from pathlib import Path
from io import BytesIO
import os
import requests

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

MODELS = [
    {"id": "openrouter/free", "name": "OpenRouter Free Router", "tag": "Auto-picks an available free model"},
    {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "Llama 3.3 70B", "tag": "Reliable all-rounder"},
    {"id": "deepseek/deepseek-r1-0528:free", "name": "DeepSeek R1", "tag": "Detailed reasoning"},
    {"id": "qwen/qwen3-coder:free", "name": "Qwen3 Coder", "tag": "Code specialist"},
    {"id": "google/gemma-3-27b-it:free", "name": "Gemma 3 27B", "tag": "Fast & concise"},
]

@app.get('/')
def index():
    return render_template('index.html', models=MODELS)

@app.post('/api/generate')
def generate():
    payload = request.get_json(silent=True) or {}
    code = (payload.get('code') or '').strip()
    files = payload.get('files') or []
    if not code and not files:
        return jsonify(error='Add source code or upload at least one file.'), 400
    model = payload.get('model') or MODELS[0]['id']
    if model != 'openrouter/free' and model not in {item['id'] for item in MODELS}:
        return jsonify(error='Choose a free model from the list.'), 400
    if len(files) > 20:
        return jsonify(error='Upload up to 20 files at a time.'), 400
    sections = []
    for item in files:
        name = str(item.get('name', 'source.txt'))[:160]
        content = str(item.get('content', ''))
        if len(content) > 100_000:
            return jsonify(error=f'{name} is larger than the 100 KB per-file limit.'), 413
        sections.append(f'### File: {name}\n```\n{content}\n```')
    source = '\n\n'.join(sections)
    if code:
        source += ('\n\n' if source else '') + '### Pasted source\n```\n' + code + '\n```'
    if len(source) > 350_000:
        return jsonify(error='The combined source is too large. Keep it under 350 KB.'), 413
    api_key = os.getenv('OPENROUTER_API_KEY', '').strip() or str(payload.get('apiKey') or '').strip()
    if not api_key:
        return jsonify(error='Add your OpenRouter API key in the key field, or set OPENROUTER_API_KEY on the server.'), 400
    prompt = """You are a senior software documentation engineer. Analyze only the supplied source. Generate accurate, useful Markdown documentation with: a project overview; setup and run instructions only when inferable (mark assumptions clearly); architecture and key modules; public APIs, functions, and classes; configuration and environment variables; a usage example; and limitations or unanswered questions. Use code examples grounded in the source. Never invent behavior. If the input is partial, say so. Return only the Markdown document.\n\nSOURCE:\n""" + source
    try:
        response = requests.post('https://openrouter.ai/api/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json', 'HTTP-Referer': request.host_url, 'X-Title': 'DocuForge'},
            json={'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0.2}, timeout=(15, 120))
        response.raise_for_status()
        data = response.json()
        documentation = data['choices'][0]['message']['content']
        if not documentation:
            raise ValueError('The model returned an empty response.')
        usage = data.get('usage', {})
        return jsonify(documentation=documentation, model=model, usage=usage)
    except requests.Timeout:
        return jsonify(error='OpenRouter timed out. Try again or choose a faster model.'), 504
    except requests.RequestException as exc:
        detail = ''
        if exc.response is not None:
            try: detail = exc.response.json().get('error', {}).get('message', '')
            except Exception: detail = exc.response.text[:240]
        return jsonify(error=detail or 'Could not reach OpenRouter. Check your API key and connection.'), 502
    except (KeyError, IndexError, ValueError) as exc:
        return jsonify(error=f'Unexpected response from the model provider: {exc}'), 502

@app.post('/api/export')
def export_markdown():
    payload = request.get_json(silent=True) or {}
    markdown = (payload.get('markdown') or '').strip()
    if not markdown:
        return jsonify(error='There is no documentation to download yet.'), 400
    return send_file(BytesIO(markdown.encode()), mimetype='text/markdown', as_attachment=True, download_name='documentation.md')

@app.errorhandler(413)
def too_large(_):
    return jsonify(error='Request is too large. Keep each upload under 100 KB and total source under 350 KB.'), 413

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.getenv('PORT', '5000')), debug=False)


