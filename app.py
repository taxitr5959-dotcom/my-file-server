import os
import boto3
from flask import Flask, request, redirect, url_for, render_template_string, Response

app = Flask(__name__)

ACCOUNT_ID = os.environ.get('CF_ACCOUNT_ID')
ACCESS_KEY = os.environ.get('CF_ACCESS_KEY')
SECRET_KEY = os.environ.get('CF_SECRET_KEY')
BUCKET_NAME = os.environ.get('CF_BUCKET_NAME', 'my-files')

s3_client = None
if ACCOUNT_ID and ACCESS_KEY and SECRET_KEY:
    s3_client = boto3.client(
        's3',
        endpoint_url=f'https://{ACCOUNT_ID}.r2.cloudflarestorage.com',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name='auto'
    )

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[SYSTEM_TERMINAL] Cloud Drive</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        * { box-sizing: border-box; font-family: 'Courier New', Courier, monospace; }
        body { background-color: #080b10; margin: 0; padding: 16px; color: #00ff66; text-shadow: 0 0 4px rgba(0,255,102,0.4); }
        .card { background: #0d1117; border: 1px solid #00ff66; border-radius: 8px; padding: 20px; max-width: 550px; margin: 0 auto; box-shadow: 0 0 15px rgba(0,255,102,0.15); }
        .header { border-bottom: 1px solid #00ff66; padding-bottom: 12px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; }
        .header h2 { margin: 0; font-size: 1.1rem; letter-spacing: 1px; color: #00ff66; }
        .status-dot { height: 10px; width: 10px; background-color: #00ff66; border-radius: 50%; display: inline-block; box-shadow: 0 0 8px #00ff66; }
        
        .breadcrumb { font-size: 0.85rem; margin-bottom: 16px; color: #00b347; }
        .breadcrumb a { color: #00ff66; text-decoration: none; border-bottom: 1px dashed #00ff66; }

        .section-box { background: #040609; border: 1px solid #005522; border-radius: 6px; padding: 14px; margin-bottom: 16px; }
        .input-style { width: 100%; padding: 10px; border: 1px solid #00aa44; border-radius: 4px; font-size: 0.85rem; background: #000; color: #00ff66; margin-bottom: 10px; }
        .input-style:focus { outline: none; border-color: #00ff66; box-shadow: 0 0 8px rgba(0,255,102,0.5); }
        
        .btn { border: 1px solid #00ff66; border-radius: 4px; padding: 10px; font-size: 0.85rem; font-weight: bold; width: 100%; cursor: pointer; transition: all 0.2s; background: #002200; color: #00ff66; display: flex; align-items: center; justify-content: center; gap: 8px; }
        .btn:hover { background: #00ff66; color: #000; box-shadow: 0 0 10px #00ff66; }
        .btn-success { border-color: #ffb700; color: #ffb700; background: #221800; }
        .btn-success:hover { background: #ffb700; color: #000; box-shadow: 0 0 10px #ffb700; }

        /* Cyber Progress Bar */
        .progress-container { display: none; margin-top: 12px; background: #000; border: 1px solid #00ff66; border-radius: 4px; padding: 2px; position: relative; height: 20px; }
        .progress-bar { width: 0%; height: 100%; background: #00ff66; transition: width 0.1s; }
        .progress-text { position: absolute; width: 100%; text-align: center; font-size: 0.75rem; color: #000; font-weight: bold; line-height: 20px; text-shadow: none; top:0; }

        .file-list { list-style: none; padding: 0; margin: 0; }
        .file-item { display: flex; align-items: center; justify-content: space-between; padding: 10px; background: #000; border: 1px solid #003311; border-radius: 4px; margin-bottom: 6px; }
        .file-item:hover { border-color: #00ff66; }
        .file-info { display: flex; align-items: center; gap: 10px; text-decoration: none; color: #00ff66; flex-grow: 1; overflow: hidden; }
        .folder-link { color: #ffb700 !important; }
        .file-name { font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        
        .terminal-log { font-size: 0.75rem; color: #00aa44; margin-top: 15px; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h2><i class="fa-solid fa-terminal"></i> R2_VAULT // ROOT</h2>
            <span class="status-dot"></span>
        </div>
        
        <div class="breadcrumb">
            SYSTEM_PATH: <a href="{{ url_for('index') }}">/ROOT</a>
            {% if current_dir %}
                / {{ current_dir }}
            {% endif %}
        </div>

        <!-- UPLOAD SECTION -->
        <div class="section-box">
            <form id="uploadForm" action="{{ url_for('upload_file') }}" method="post" enctype="multipart/form-data">
                <input type="hidden" name="subpath" value="{{ current_dir }}">
                <input type="file" name="file" id="fileInput" class="input-style" required>
                <button type="submit" class="btn"><i class="fa-solid fa-upload"></i> INJECT_FILE_TO_CLOUD</button>
            </form>
            <div class="progress-container" id="progressBox">
                <div class="progress-bar" id="progressBar"></div>
                <div class="progress-text" id="progressText">0%</div>
            </div>
        </div>

        <!-- CREATE FOLDER SECTION -->
        <div class="section-box">
            <form action="{{ url_for('create_folder') }}" method="post" style="display: flex; gap: 8px;">
                <input type="hidden" name="subpath" value="{{ current_dir }}">
                <input type="text" name="foldername" placeholder="NEW_DIR_NAME..." class="input-style" style="margin:0;" required>
                <button type="submit" class="btn btn-success" style="width: auto; white-space: nowrap;"><i class="fa-solid fa-folder-plus"></i> MKDIR</button>
            </form>
        </div>

        <h3 style="font-size: 0.9rem; border-bottom: 1px solid #003311; padding-bottom: 5px;">> DIRECTORY_CONTENTS</h3>
        <ul class="file-list">
            {% for item in items %}
                <li class="file-item" onmousedown="startPress('{{ item.name }}', {{ 'true' if item.is_dir else 'false' }})" onmouseup="cancelPress()" ontouchstart="startPress('{{ item.name }}', {{ 'true' if item.is_dir else 'false' }})" ontouchend="cancelPress()">
                    {% if item.is_dir %}
                        <a href="{{ url_for('index', subpath=(current_dir + '/' + item.name) if current_dir else item.name) }}" class="file-info folder-link">
                            <i class="fa-solid fa-folder"></i>
                            <span class="file-name">{{ item.name }}/</span>
                        </a>
                    {% else %}
                        <a href="{{ url_for('download_file', filename=(current_dir + '/' + item.name) if current_dir else item.name) }}" target="_blank" class="file-info">
                            <i class="fa-solid fa-file-code"></i>
                            <span class="file-name">{{ item.name }}</span>
                        </a>
                    {% endif %}
                </li>
            {% else %}
                <li style="color: #006622; text-align: center; padding: 15px; font-size: 0.8rem;">[NO_DATA_FOUND_IN_THIS_DIRECTORY]</li>
            {% endfor %}
        </ul>
        <div class="terminal-log">[HOLD_ITEM_TO_PURGE_DATA]</div>
    </div>

    <script>
        // JS Upload with Cyber Progress Bar
        document.getElementById('uploadForm').onsubmit = function(e) {
            e.preventDefault();
            var fileInput = document.getElementById('fileInput');
            if (fileInput.files.length === 0) return;

            var formData = new FormData(this);
            var xhr = new XMLHttpRequest();

            var progressBox = document.getElementById('progressBox');
            var progressBar = document.getElementById('progressBar');
            var progressText = document.getElementById('progressText');

            progressBox.style.display = 'block';

            xhr.upload.onprogress = function(e) {
                if (e.lengthComputable) {
                    var percent = Math.round((e.loaded / e.total) * 100);
                    progressBar.style.width = percent + '%';
                    progressText.innerText = 'UPLOADING... ' + percent + '% (' + (e.loaded / (1024*1024)).toFixed(1) + 'MB)';
                }
            };

            xhr.onload = function() {
                if (xhr.status == 200) {
                    window.location.reload();
                } else {
                    alert('[ERROR] TRANSMISSION_FAILED');
                }
            };

            xhr.open('POST', this.action, true);
            xhr.send(formData);
        };

        // Long Press Delete
        let pressTimer;
        function startPress(name, isDir) {
            pressTimer = setTimeout(() => {
                const typeStr = isDir ? 'DIRECTORY' : 'FILE';
                if (confirm(`PURGE ${typeStr} "${name}" FROM R2 STORAGE?`)) {
                    const form = document.createElement('form');
                    form.method = 'POST';
                    form.action = '{{ url_for("delete_item") }}';
                    
                    const pathInput = document.createElement('input');
                    pathInput.type = 'hidden';
                    pathInput.name = 'item_path';
                    pathInput.value = '{{ current_dir }}/' + name;
                    
                    form.appendChild(pathInput);
                    document.body.appendChild(form);
                    form.submit();
                }
            }, 800);
        }
        function cancelPress() { clearTimeout(pressTimer); }
    </script>
</body>
</html>
'''

def get_prefix(subpath=""):
    subpath = subpath.strip("/")
    return f"{subpath}/" if subpath else ""

@app.route('/')
@app.route('/<path:subpath>')
def index(subpath=""):
    if not s3_client:
        return "[SYSTEM_ERROR] MISSING_R2_CREDENTIALS"
    
    prefix = get_prefix(subpath)
    try:
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix, Delimiter='/')
    except Exception as e:
        return f"[SYSTEM_ERROR] CONNECT_FAILED: {str(e)}"
    
    items = []
    for p in response.get('CommonPrefixes', []):
        folder_name = p['Prefix'][len(prefix):].strip('/')
        if folder_name:
            items.append({'name': folder_name, 'is_dir': True})
            
    for obj in response.get('Contents', []):
        file_name = obj['Key'][len(prefix):]
        if file_name and file_name != '.keep' and not file_name.endswith('/'):
            items.append({'name': file_name, 'is_dir': False})
            
    return render_template_string(HTML_TEMPLATE, items=items, current_dir=subpath)

@app.route('/upload', methods=['POST'])
def upload_file():
    subpath = request.form.get('subpath', '')
    prefix = get_prefix(subpath)
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            key = f"{prefix}{file.filename}"
            s3_client.upload_fileobj(file, BUCKET_NAME, key)
    return redirect(url_for('index', subpath=subpath))

@app.route('/create_folder', methods=['POST'])
def create_folder():
    subpath = request.form.get('subpath', '')
    foldername = request.form.get('foldername', '').strip()
    if foldername:
        prefix = get_prefix(subpath)
        key = f"{prefix}{foldername}/.keep"
        s3_client.put_object(Bucket=BUCKET_NAME, Key=key, Body=b'')
    return redirect(url_for('index', subpath=subpath))

@app.route('/download/<path:filename>')
def download_file(filename):
    filename = filename.lstrip('/')
    obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=filename)
    return Response(
        obj['Body'].read(),
        headers={"Content-Disposition": f"inline; filename={os.path.basename(filename)}"}
    )

@app.route('/delete', methods=['POST'])
def delete_item():
    item_path = request.form.get('item_path', '').strip('/')
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=item_path)
    if 'Contents' in response:
        delete_keys = [{'Key': obj['Key']} for obj in response['Contents']]
        s3_client.delete_objects(Bucket=BUCKET_NAME, Delete={'Objects': delete_keys})
        
    parent_dir = os.path.dirname(item_path)
    return redirect(url_for('index', subpath=parent_dir))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
