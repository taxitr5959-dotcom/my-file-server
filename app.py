from flask import Flask, send_from_directory
import os

app = Flask(__name__)
FOLDER = 'files'
os.makedirs(FOLDER, exist_ok=True)

@app.route('/')
def list_files():
    files = os.listdir(FOLDER)
    items = ''.join([f'<li><a href="/files/{f}">{f}</a></li>' for f in files])
    return f'<h2>My Server</h2><ul>{items}</ul>'

@app.route('/files/<filename>')
def download_file(filename):
    return send_from_directory(FOLDER, filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
