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
    <title>R2 CyberDrive - Enterprise File System</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * { box-sizing: border-box; font-family: 'Consolas', 'Courier New', monospace; }
        body { background-color: #05080c; margin: 0; padding: 15px; color: #00ff66; text-shadow: 0 0 2px rgba(0,255,102,0.2); }
        
        .container { max-width: 1400px; margin: 0 auto; background: #0d1117; border: 1px solid #00ff66; border-radius: 8px; padding: 20px; box-shadow: 0 0 20px rgba(0,255,102,0.1); }
        
        .header { border-bottom: 2px solid #00ff66; padding-bottom: 12px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { margin: 0; font-size: 1.4rem; letter-spacing: 1px; color: #00ff66; display: flex; align-items: center; gap: 10px; }
        
        .nav-bar { display: flex; align-items: center; gap: 10px; background: #020406; padding: 10px 14px; border-radius: 6px; border: 1px solid #005522; margin-bottom: 15px; flex-wrap: wrap; }
        .nav-btn { background: #002200; color: #00ff66; border: 1px solid #00ff66; padding: 6px 12px; border-radius: 4px; cursor: pointer; text-decoration: none; font-size: 0.85rem; font-weight: bold; }
        .nav-btn:hover { background: #00ff66; color: #000; }
        .path-display { font-size: 0.9rem; color: #00ff66; word-break: break-all; flex-grow: 1; }

        /* Drag and Drop Zone */
        .drop-zone { border: 2px dashed #00ff66; background: rgba(0,255,102,0.02); border-radius: 6px; padding: 25px 15px; text-align: center; cursor: pointer; margin-bottom: 15px; transition: all 0.2s; }
        .drop-zone.dragover { background: rgba(0,255,102,0.15); border-color: #ffffff; }
        .drop-zone i { font-size: 2rem; margin-bottom: 8px; color: #00ff66; }
        
        .action-row { display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }
        .input-text { background: #000; border: 1px solid #00aa44; color: #00ff66; padding: 8px 12px; border-radius: 4px; font-size: 0.85rem; }
        .btn { background: #002200; border: 1px solid #00ff66; color: #00ff66; padding: 8px 14px; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-weight: bold; display: inline-flex; align-items: center; gap: 6px; }
        .btn:hover { background: #00ff66; color: #000; }
        .btn-danger { border-color: #ff3333; color: #ff3333; background: #220000; }
        .btn-danger:hover { background: #ff3333; color: #fff; }

        /* Progress Bar */
        .progress-container { display: none; margin-bottom: 15px; background: #000; border: 1px solid #00ff66; border-radius: 4px; position: relative; height: 24px; }
        .progress-bar { width: 0%; height: 100%; background: #00ff66; transition: width 0.1s; }
        .progress-text { position: absolute; width: 100%; text-align: center; font-size: 0.8rem; color: #000; font-weight: bold; line-height: 24px; top: 0; left: 0; }

        /* File Grid System */
        .file-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; margin-top: 15px; }
        .file-card { background: #020406; border: 1px solid #003311; border-radius: 6px; padding: 10px; position: relative; display: flex; flex-direction: column; justify-content: space-between; height: 160px; transition: border-color 0.2s; }
        .file-card:hover { border-color: #00ff66; }
        
        .card-select { position: absolute; top: 8px; left: 8px; z-index: 5; transform: scale(1.2); cursor: pointer; }
        
        .card-preview { height: 90px; display: flex; align-items: center; justify-content: center; cursor: pointer; overflow: hidden; margin-top: 10px; }
        .card-preview img { max-width: 100%; max-height: 100%; object-fit: cover; border-radius: 4px; border: 1px solid #005522; }
        .card-preview i { font-size: 2.8rem; color: #00ff66; }
        .folder-icon { color: #ffb700 !important; }

        .card-info { text-align: center; margin-top: 6px; }
        .card-title { font-size: 0.8rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; color: #00ff66; text-decoration: none; }
        
        .card-actions { display: flex; justify-content: center; gap: 8px; margin-top: 4px; }
        .icon-btn { background: transparent; border: none; color: #00ff66; cursor: pointer; font-size: 0.85rem; padding: 4px; }
        .icon-btn:hover { color: #fff; }
        .icon-btn-del { color: #ff3333; }

        /* Lightbox Modal */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.92); z-index: 1000; justify-content: center; align-items: center; }
        .modal-content { max-width: 90%; max-height: 85%; object-fit: contain; border: 2px solid #00ff66; box-shadow: 0 0 20px #00ff66; }
        .modal-nav { position: absolute; top: 50%; transform: translateY(-50%); font-size: 2.5rem; color: #00ff66; cursor: pointer; padding: 15px; background: rgba(0,0,0,0.5); border-radius: 50%; user-select: none; }
        .modal-prev { left: 20px; }
        .modal-next { right: 20px; }
        .modal-close { position: absolute; top: 20px; right: 30px; font-size: 2.5rem; color: #ff3333; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fa-solid fa-server"></i> R2_VAULT // FILE_MANAGER</h1>
            <div>STATUS: <span style="color:#00ff66;">ONLINE</span></div>
        </div>

        <!-- Path Navigation -->
        <div class="nav-bar">
            {% if current_dir %}
                {% set parent_dir = current_dir.rsplit('/', 1)[0] if '/' in current_dir else '' %}
                <a href="{{ url_for('index', subpath=parent_dir) }}" class="nav-btn"><i class="fa-solid fa-arrow-left"></i> [BACK]</a>
            {% endif %}
            <a href="{{ url_for('index') }}" class="nav-btn"><i class="fa-solid fa-house"></i> ROOT</a>
            <div class="path-display">PATH: /{{ current_dir }}</div>
        </div>

        <!-- Drag & Drop Area -->
        <div class="drop-zone" id="dropZone" onclick="document.getElementById('fileInput').click();">
            <i class="fa-solid fa-cloud-arrow-up"></i>
            <div><strong>CLICK OR DRAG & DROP FILES HERE</strong></div>
            <div style="font-size: 0.75rem; color: #00aa44; margin-top: 4px;">รองรับการอัปโหลดหลายไฟล์พร้อมกัน (Bulk Upload Supported)</div>
            <input type="file" id="fileInput" multiple style="display: none;" onchange="uploadFiles(this.files)">
        </div>

        <!-- Progress Bar -->
        <div class="progress-container" id="progressBox">
            <div class="progress-bar" id="progressBar"></div>
            <div class="progress-text" id="progressText">0%</div>
        </div>

        <!-- Action Bar -->
        <div class="action-row">
            <form action="{{ url_for('create_folder') }}" method="post" style="display: flex; gap: 6px;">
                <input type="hidden" name="subpath" value="{{ current_dir }}">
                <input type="text" name="foldername" placeholder="New Folder Name..." class="input-text" required>
                <button type="submit" class="btn"><i class="fa-solid fa-folder-plus"></i> MKDIR</button>
            </form>

            <button onclick="deleteSelected()" class="btn btn-danger"><i class="fa-solid fa-trash"></i> DELETE SELECTED</button>
        </div>

        <!-- File Grid -->
        <div class="file-grid">
            {% for item in items %}
                {% set item_path = (current_dir + '/' + item.name) if current_dir else item.name %}
                <div class="file-card">
                    <input type="checkbox" class="card-select file-checkbox" value="{{ item_path }}">
                    
                    {% if item.is_dir %}
                        <a href="{{ url_for('index', subpath=item_path) }}" class="card-preview">
                            <i class="fa-solid fa-folder folder-icon"></i>
                        </a>
                        <div class="card-info">
                            <a href="{{ url_for('index', subpath=item_path) }}" class="card-title">{{ item.name }}/</a>
                        </div>
                    {% else %}
                        {% if item.is_img %}
                            <div class="card-preview" onclick="openLightbox('{{ url_for('file_action', filename=item_path) }}')">
                                <img src="{{ url_for('file_action', filename=item_path) }}" class="img-item" alt="preview">
                            </div>
                        {% else %}
                            <a href="{{ url_for('file_action', filename=item_path) }}" target="_blank" class="card-preview">
                                <i class="fa-solid fa-file-code"></i>
                            </a>
                        {% endif %}
                        <div class="card-info">
                            <a href="{{ url_for('file_action', filename=item_path) }}" target="_blank" class="card-title">{{ item.name }}</a>
                        </div>
                    {% endif %}

                    <div class="card-actions">
                        {% if not item.is_dir %}
                            <a href="{{ url_for('file_action', filename=item_path, download='1') }}" class="icon-btn" title="Download">
                                <i class="fa-solid fa-download"></i>
                            </a>
                        {% endif %}
                        <button onclick="deleteSingle('{{ item_path }}')" class="icon-btn icon-btn-del" title="Delete">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>
            {% else %}
                <div style="grid-column: 1 / -1; text-align: center; color: #006622; padding: 40px;">
                    [DIRECTORY IS EMPTY]
                </div>
            {% endfor %}
        </div>
    </div>

    <!-- Lightbox Modal -->
    <div class="modal" id="lightbox">
        <span class="modal-close" onclick="closeLightbox()">&times;</span>
        <span class="modal-nav modal-prev" onclick="changeSlide(-1)">&#10094;</span>
        <img class="modal-content" id="modalImg">
        <span class="modal-nav modal-next" onclick="changeSlide(1)">&#10095;</span>
    </div>

    <script>
        const currentSubpath = "{{ current_dir }}";

        // Drag & Drop Handling
        const dropZone = document.getElementById('dropZone');
        ['dragenter', 'dragover'].forEach(name => {
            dropZone.addEventListener(name, (e) => { e.preventDefault(); dropZone.classList.add('dragover'); }, false);
        });
        ['dragleave', 'drop'].forEach(name => {
            dropZone.addEventListener(name, (e) => { e.preventDefault(); dropZone.classList.remove('dragover'); }, false);
        });
        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            uploadFiles(dt.files);
        });

        // Batch Upload Multiple Files
        function uploadFiles(files) {
            if (files.length === 0) return;
            
            const formData = new FormData();
            formData.append('subpath', currentSubpath);
            for (let i = 0; i < files.length; i++) {
                formData.append('files', files[i]);
            }

            const xhr = new XMLHttpRequest();
            const progressBox = document.getElementById('progressBox');
            const progressBar = document.getElementById('progressBar');
            const progressText = document.getElementById('progressText');

            progressBox.style.display = 'block';

            xhr.upload.onprogress = function(e) {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    progressBar.style.width = percent + '%';
                    progressText.innerText = `UPLOADING ${files.length} FILES... ${percent}% (${(e.loaded / (1024*1024)).toFixed(1)}MB)`;
                }
            };

            xhr.onload = function() {
                if (xhr.status === 200) {
                    window.location.reload();
                } else {
                    alert('[ERROR] UPLOAD FAILED');
                }
            };

            xhr.open('POST', '{{ url_for("upload_files") }}', true);
            xhr.send(formData);
        }

        // Delete Single / Multiple Items
        function deleteSingle(path) {
            if (confirm(`Delete "${path}"?`)) {
                sendDeleteRequest([path]);
            }
        }

        function deleteSelected() {
            const checkedBoxes = document.querySelectorAll('.file-checkbox:checked');
            const paths = Array.from(checkedBoxes).map(cb => cb.value);
            if (paths.length === 0) {
                alert('โปรดเลือกไฟล์หรือโฟลเดอร์ที่ต้องการลบ');
                return;
            }
            if (confirm(`Delete ${paths.length} selected item(s)?`)) {
                sendDeleteRequest(paths);
            }
        }

        function sendDeleteRequest(paths) {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '{{ url_for("delete_items") }}';
            
            paths.forEach(p => {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'item_paths';
                input.value = p;
                form.appendChild(input);
            });

            document.body.appendChild(form);
            form.submit();
        }

        // Lightbox Image Viewer Logic
        let imgList = [];
        let currentIndex = 0;

        document.addEventListener("DOMContentLoaded", () => {
            imgList = Array.from(document.querySelectorAll('.img-item')).map(img => img.src);
        });

        function openLightbox(src) {
            currentIndex = imgList.indexOf(src);
            document.getElementById('modalImg').src = src;
            document.getElementById('lightbox').style.display = 'flex';
        }

        function closeLightbox() {
            document.getElementById('lightbox').style.display = 'none';
        }

        function changeSlide(direction) {
            if (imgList.length === 0) return;
            currentIndex = (currentIndex + direction + imgList.length) % imgList.length;
            document.getElementById('modalImg').src = imgList[currentIndex];
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
    for p in response.get('CommonPrefixes', []):
        folder_name = p['Prefix'][len(prefix):].strip('/')
        if folder_name:
            items.append({'name': folder_name, 'is_dir': True, 'is_img': False})
            
    img_exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
    for obj in response.get('Contents', []):
        file_name = obj['Key'][len(prefix):]
        if file_name and file_name != '.keep' and not file_name.endswith('/'):
            is_img = file_name.lower().endswith(img_exts)
            items.append({'name': file_name, 'is_dir': False, 'is_img': is_img})
            
    return render_template_string(HTML_TEMPLATE, items=items, current_dir=subpath)

@app.route('/upload', methods=['POST'])
def upload_files():
    subpath = request.form.get('subpath', '')
    prefix = get_prefix(subpath)
    files = request.files.getlist('files')
    
    for file in files:
        if file and file.filename != '':
            key = f"{prefix}{file.filename}"
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
def delete_items():
    item_paths = request.form.getlist('item_paths')
    subpath = ""
    
    for item_path in item_paths:
        item_path = item_path.strip('/')
        subpath = os.path.dirname(item_path)
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=item_path)
        if 'Contents' in response:
            delete_keys = [{'Key': obj['Key']} for obj in response['Contents']]
            s3_client.delete_objects(Bucket=BUCKET_NAME, Delete={'Objects': delete_keys})

    return redirect(url_for('index', subpath=subpath))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
