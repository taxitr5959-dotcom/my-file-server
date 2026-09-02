import os
import mimetypes
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
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * { box-sizing: border-box; font-family: 'Courier New', Courier, monospace; }
        body { background-color: #080b10; margin: 0; padding: 12px; color: #00ff66; text-shadow: 0 0 3px rgba(0,255,102,0.3); }
        .card { background: #0d1117; border: 1px solid #00ff66; border-radius: 8px; padding: 16px; max-width: 550px; margin: 0 auto; box-shadow: 0 0 15px rgba(0,255,102,0.15); }
        
        .header { border-bottom: 1px solid #00ff66; padding-bottom: 10px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; }
        .header h2 { margin: 0; font-size: 1.1rem; letter-spacing: 1px; color: #00ff66; }
        .status-dot { height: 10px; width: 10px; background-color: #00ff66; border-radius: 50%; display: inline-block; box-shadow: 0 0 8px #00ff66; }
        
        .breadcrumb { font-size: 0.85rem; margin-bottom: 14px; color: #00b347; word-break: break-all; }
        .breadcrumb a { color: #00ff66; text-decoration: none; border-bottom: 1px dashed #00ff66; }

        .section-box { background: #040609; border: 1px solid #005522; border-radius: 6px; padding: 12px; margin-bottom: 14px; }
        
        /* Styled File Input */
        .file-input-wrapper { position: relative; margin-bottom: 10px; }
        .input-style { width: 100%; padding: 10px; border: 1px solid #00aa44; border-radius: 4px; font-size: 0.85rem; background: #000; color: #00ff66; }
        .input-style:focus { outline: none; border-color: #00ff66; box-shadow: 0 0 8px rgba(0,255,102,0.5); }
        
        .btn { border: 1px solid #00ff66; border-radius: 4px; padding: 10px; font-size: 0.85rem; font-weight: bold; width: 100%; cursor: pointer; transition: all 0.2s; background: #002200; color: #00ff66; display: flex; align-items: center; justify-content: center; gap: 8px; }
        .btn:hover, .btn:active { background: #00ff66; color: #000; box-shadow: 0 0 10px #00ff66; }
        .btn-success { border-color: #ffb700; color: #ffb700; background: #221800; }
        .btn-success:hover, .btn-success:active { background: #ffb700; color: #000; box-shadow: 0 0 10px #ffb700; }

        /* Cyber Progress Bar */
        .progress-container { display: none; margin-top: 10px; background: #000; border: 1px solid #00ff66; border-radius: 4px; padding: 2px; position: relative; height: 22px; }
        .progress-bar { width: 0%; height: 100%; background: #00ff66; transition: width 0.1s; }
        .progress-text { position: absolute; width: 100%; text-align: center; font-size: 0.75rem; color: #000; font-weight: bold; line-height: 22px; text-shadow: none; top:0; left:0; }

        /* File List UI */
        .file-list { list-style: none; padding: 0; margin: 0; }
        .file-item { display: flex; align-items: center; justify-content: space-between; padding: 8px 10px; background: #000; border: 1px solid #003311; border-radius: 4px; margin-bottom: 8px; gap: 8px; }
        .file-item:hover { border-color: #00ff66; }
        
        .file-main { display: flex; align-items: center; gap: 10px; text-decoration: none; color: #00ff66; flex-grow: 1; overflow: hidden; }
        .file-name { font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .folder-link { color: #ffb700 !important; }
        
        /* Thumbnails for images */
        .img-thumb { width: 32px; height: 32px; object-fit: cover; border-radius: 3px; border: 1px solid #00ff66; }
        
        /* Action Buttons */
        .action-btns { display: flex; gap: 6px; align-items: center; }
        .icon-btn { background: transparent; border: 1px solid #005522; color: #00ff66; padding: 6px 8px; border-radius: 3px; cursor: pointer; text-decoration: none; font-size: 0.8rem; display: inline-flex; align-items: center; justify-content: center; }
        .icon-btn:hover { background: #00ff66; color: #000; }
        .icon-btn-del { border-color: #ff3333; color: #ff3333; }
        .icon-btn-del:hover { background: #ff3333; color: #fff; box-shadow: 0 0 8px #ff3333; }
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
                <div class="file-input-wrapper">
                    <input type="file" name="file" id="fileInput" class="input-style" required>
                </div>
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

        <h3 style="font-size: 0.9rem; border-bottom: 1px solid #003311; padding-bottom: 6px; margin-top: 16px;">> DIRECTORY_CONTENTS</h3>
        <ul class="file-list">
            {% for item in items %}
                <li class="file-item">
                    {% if item.is_dir %}
                        <a href="{{ url_for('index', subpath=(current_dir + '/' + item.name) if current_dir else item.name) }}" class="file-main folder-link">
                            <i class="fa-solid fa-folder" style="font-size: 1.1rem;"></i>
                            <span class="file-name">{{ item.name }}/</span>
                        </a>
                        <div class="action-btns">
                            <button onclick="deleteItem('{{ item.name }}', true)" class="icon-btn icon-btn-del" title="Delete Folder">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </div>
                    {% else %}
                        {% set file_path = (current_dir + '/' + item.name) if current_dir else item.name %}
                        <a href="{{ url_for('file_action', filename=file_path) }}" target="_blank" class="file-main">
                            {% if item.is_img %}
                                <img src="{{ url_for('file_action', filename=file_path) }}" class="img-thumb" alt="thumb">
                            {% else %}
                                <i class="fa-solid fa-file-code" style="font-size: 1.1rem;"></i>
                            {% endif %}
                            <span class="file-name">{{ item.name }}</span>
                        </a>
                        <div class="action-btns">
                            <a href="{{ url_for('file_action', filename=file_path, download='1') }}" class="icon-btn" title="Download File">
                                <i class="fa-solid fa-download"></i>
                            </a>
                            <button onclick="deleteItem('{{ item.name }}', false)" class="icon-btn icon-btn-del" title="Delete File">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </div>
                    {% endif %}
                </li>
            {% else %}
                <li style="color: #006622; text-align: center; padding: 15px; font-size: 0.8rem;">[NO_DATA_FOUND_IN_THIS_DIRECTORY]</li>
            {% endfor %}
        </ul>
    </div>

    <script>
        // JS Upload Progress
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

        // Delete Function
        function deleteItem(name, isDir) {
            const typeStr = isDir ? 'DIRECTORY' : 'FILE';
            if (confirm(`PURGE ${typeStr} "${name}" FROM R2 STORAGE?`)) {
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = '{{ url_for("delete_item") }}';
                
                const pathInput = document.createElement('input');
                pathInput.type = 'hidden';
                pathInput.name = 'item_path';
                pathInput.value = '{{ (current_dir + "/" if current_dir else "") }}' + name;
                
                form.appendChild(pathInput);
                document.body.appendChild(form);
                form.submit();
            }
        }
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
    # Folders
    for p in response.get('CommonPrefixes', []):
        folder_name = p['Prefix'][len(prefix):].strip('/')
        if folder_name:
            items.append({'name': folder_name, 'is_dir': True, 'is_img': False})
            
    # Files
    img_exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
    for obj in response.get('Contents', []):
        file_name = obj['Key'][len(prefix):]
        if file_name and file_name != '.keep' and not file_name.endswith('/'):
            is_img = file_name.lower().endswith(img_exts)
            items.append({'name': file_name, 'is_dir': False, 'is_img': is_img})
            
    return render_template_string(HTML_TEMPLATE, items=items, current_dir=subpath)

@app.route('/upload', methods=['POST'])
def upload_file():
    subpath = request.form.get('subpath', '')
    prefix = get_prefix(subpath)
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            key = f"{prefix}{file.filename}"
            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(file.filename)
            extra_args = {'ContentType': mime_type} if mime_type else {}
            s3_client.upload_fileobj(file, BUCKET_NAME, key, ExtraArgs=extra_args)
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

@app.route('/file/<path:filename>')
def file_action(filename):
    filename = filename.lstrip('/')
    obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=filename)
    
    # MIME type handling
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        mime_type = obj.get('ContentType', 'application/octet-stream')

    is_download = request.args.get('download') == '1'
    disposition = "attachment" if is_download else "inline"
    
    return Response(
        obj['Body'].read(),
        mimetype=mime_type,
        headers={"Content-Disposition": f"{disposition}; filename=\"{os.path.basename(filename)}\""}
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
