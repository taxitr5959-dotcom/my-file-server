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
    <title>R2 CYBER_VAULT // SYSTEM</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * { box-sizing: border-box; font-family: 'Consolas', 'Courier New', monospace; }
        html, body { height: 100%; margin: 0; padding: 0; background-color: #030308; color: #00ff66; }
        
        /* Layout เต็มหน้าจอ 100vh ไม่กุดเป็นกางเกงขาสั้น */
        .page-wrapper { min-height: 100vh; padding: 10px; display: flex; flex-direction: column; background: radial-gradient(circle at center, #0a0a16 0%, #020205 100%); }
        .container { flex: 1; max-width: 1400px; width: 100%; margin: 0 auto; background: rgba(10, 10, 20, 0.95); border: 2px solid #bd00ff; border-radius: 10px; padding: 15px; box-shadow: 0 0 15px rgba(189, 0, 255, 0.3), inset 0 0 15px rgba(0, 240, 255, 0.1); display: flex; flex-direction: column; }
        
        /* Header & Neon Cyberpunk Colors */
        .header { border-bottom: 2px solid #ff0055; padding-bottom: 10px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { margin: 0; font-size: 1.2rem; letter-spacing: 1px; color: #00f0ff; text-shadow: 0 0 8px #00f0ff; display: flex; align-items: center; gap: 8px; }
        
        /* ไฟสเตตัส ONLINE กระพริบแบบไฟเลี้ยว */
        .status-online { color: #00ff66; font-weight: bold; text-shadow: 0 0 8px #00ff66; animation: blinker 1s cubic-bezier(0.5, 0, 1, 1) infinite alternate; }
        @keyframes blinker { from { opacity: 1.0; } to { opacity: 0.15; } }

        /* Path Navigation Bar */
        .nav-bar { display: flex; align-items: center; gap: 10px; background: #080812; padding: 10px; border-radius: 6px; border: 1px solid #ff6600; margin-bottom: 12px; flex-wrap: wrap; box-shadow: 0 0 8px rgba(255, 102, 0, 0.2); }
        .nav-btn { background: #1a0033; color: #ff0055; border: 1px solid #ff0055; padding: 6px 12px; border-radius: 4px; cursor: pointer; text-decoration: none; font-size: 0.8rem; font-weight: bold; transition: 0.2s; }
        .nav-btn:hover { background: #ff0055; color: #fff; box-shadow: 0 0 10px #ff0055; }
        .path-display { font-size: 0.85rem; color: #00f0ff; text-shadow: 0 0 5px #00f0ff; word-break: break-all; flex-grow: 1; }

        /* Drag and Drop Zone */
        .drop-zone { border: 2px dashed #00f0ff; background: rgba(0, 240, 255, 0.03); border-radius: 8px; padding: 20px 10px; text-align: center; cursor: pointer; margin-bottom: 12px; transition: all 0.2s; box-shadow: 0 0 10px rgba(0, 240, 255, 0.1); }
        .drop-zone:hover, .drop-zone.dragover { background: rgba(0, 240, 255, 0.15); border-color: #ff0055; box-shadow: 0 0 15px #ff0055; }
        .drop-zone i { font-size: 2rem; margin-bottom: 6px; color: #00f0ff; text-shadow: 0 0 8px #00f0ff; }

        /* Action Controls & Input Bar */
        .action-row { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; justify-content: space-between; align-items: center; }
        .input-text { background: #000; border: 1px solid #bd00ff; color: #00f0ff; padding: 8px; border-radius: 4px; font-size: 0.8rem; outline: none; }
        .input-text:focus { border-color: #00f0ff; box-shadow: 0 0 8px #00f0ff; }
        
        .btn { background: #0d001a; border: 1px solid #bd00ff; color: #bd00ff; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; font-weight: bold; display: inline-flex; align-items: center; gap: 6px; transition: 0.2s; }
        .btn:hover { background: #bd00ff; color: #fff; box-shadow: 0 0 10px #bd00ff; }
        .btn-danger { border-color: #ff0055; color: #ff0055; background: #1a000d; }
        .btn-danger:hover { background: #ff0055; color: #fff; box-shadow: 0 0 10px #ff0055; }

        /* Progress Bar - ปรับปรุงตัวหนังสือสีแดงเด่นไม่จม */
        .progress-container { display: none; margin-bottom: 12px; background: #000; border: 2px solid #ff6600; border-radius: 6px; position: relative; height: 26px; overflow: hidden; box-shadow: 0 0 10px rgba(255,102,0,0.3); }
        .progress-bar { width: 0%; height: 100%; background: linear-gradient(90deg, #00ff66, #00f0ff); transition: width 0.1s; }
        .progress-text { position: absolute; width: 100%; text-align: center; font-size: 0.85rem; color: #ff0055; font-weight: 900; line-height: 24px; top: 0; left: 0; text-shadow: 0 0 3px #000, 0 0 8px #fff; z-index: 10; }

        /* View Mode Switcher Controls */
        .view-switchers { display: flex; gap: 4px; background: #000; border: 1px solid #ff6600; border-radius: 4px; padding: 2px; }
        .view-btn { background: transparent; border: none; color: #ff6600; padding: 6px 10px; cursor: pointer; border-radius: 3px; font-weight: bold; }
        .view-btn.active { background: #ff6600; color: #000; box-shadow: 0 0 8px #ff6600; }

        /* Content Area Container */
        .content-area { flex: 1; border: 1px solid #330066; border-radius: 6px; padding: 12px; background: rgba(3, 3, 10, 0.8); min-height: 320px; }

        /* VIEW 1: GRID MODE (ตารางสี่เหลี่ยม Cyberpunk) */
        .view-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(145px, 1fr)); gap: 12px; }
        .view-grid .file-card { background: #060612; border: 1px solid #bd00ff; border-radius: 6px; padding: 8px; position: relative; display: flex; flex-direction: column; justify-content: space-between; height: 165px; transition: all 0.2s; }
        .view-grid .file-card:hover { border-color: #00f0ff; box-shadow: 0 0 12px #00f0ff; transform: translateY(-2px); }
        .view-grid .card-preview { height: 95px; display: flex; align-items: center; justify-content: center; cursor: pointer; overflow: hidden; margin-top: 12px; }
        .view-grid .card-preview img { max-width: 100%; max-height: 100%; object-fit: cover; border-radius: 4px; border: 1px solid #330066; }
        .view-grid .card-preview i { font-size: 2.5rem; color: #00f0ff; text-shadow: 0 0 8px #00f0ff; }
        .view-grid .folder-icon { color: #ff6600 !important; text-shadow: 0 0 8px #ff6600 !important; }
        .view-grid .card-info { text-align: center; margin-top: 4px; }
        .view-grid .card-title { font-size: 0.75rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; color: #00ff66; text-decoration: none; }
        .view-grid .card-actions { display: flex; justify-content: center; gap: 10px; margin-top: 2px; }

        /* VIEW 2: LIST MODE (ตารางแนวนอน) */
        .view-list { display: flex; flex-direction: column; gap: 6px; }
        .view-list .file-card { background: #060612; border: 1px solid #330066; border-radius: 4px; padding: 8px 12px; display: flex; align-items: center; gap: 12px; justify-content: space-between; transition: 0.2s; }
        .view-list .file-card:hover { border-color: #ff0055; box-shadow: 0 0 10px rgba(255,0,85,0.3); background: #0c0c24; }
        .view-list .card-preview { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; }
        .view-list .card-preview img { width: 32px; height: 32px; object-fit: cover; border-radius: 3px; }
        .view-list .card-preview i { font-size: 1.3rem; color: #00f0ff; }
        .view-list .folder-icon { color: #ff6600 !important; }
        .view-list .card-info { flex-grow: 1; overflow: hidden; }
        .view-list .card-title { font-size: 0.85rem; color: #00ff66; text-decoration: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; }
        .view-list .card-actions { display: flex; gap: 12px; align-items: center; }

        .card-select { transform: scale(1.1); cursor: pointer; accent-color: #ff0055; }
        .icon-btn { background: transparent; border: none; color: #00f0ff; cursor: pointer; font-size: 0.9rem; padding: 4px; transition: 0.2s; }
        .icon-btn:hover { color: #fff; text-shadow: 0 0 8px #00f0ff; }
        .icon-btn-del { color: #ff0055; }
        .icon-btn-del:hover { color: #ff5588; text-shadow: 0 0 8px #ff0055; }

        /* Lightbox Modal */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.92); z-index: 1000; justify-content: center; align-items: center; }
        .modal-content { max-width: 90%; max-height: 85%; object-fit: contain; border: 2px solid #00f0ff; box-shadow: 0 0 20px #00f0ff; }
        .modal-nav { position: absolute; top: 50%; transform: translateY(-50%); font-size: 2.2rem; color: #00f0ff; cursor: pointer; padding: 12px; background: rgba(0,0,0,0.6); border-radius: 50%; user-select: none; }
        .modal-prev { left: 15px; }
        .modal-next { right: 15px; }
        .modal-close { position: absolute; top: 15px; right: 25px; font-size: 2.2rem; color: #ff0055; cursor: pointer; }
    </style>
</head>
<body>
    <div class="page-wrapper">
        <div class="container">
            <div class="header">
                <h1><i class="fa-solid fa-microchip"></i> R2_CYBER_VAULT</h1>
                <div style="font-size: 0.85rem;">SYSTEM_STATUS: <span class="status-online">● ONLINE</span></div>
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
                <div style="font-size: 0.75rem; color: #ff6600; margin-top: 4px;">TARGET_DIR: /{{ current_dir if current_dir else 'ROOT' }}</div>
                <input type="file" id="fileInput" multiple style="display: none;" onchange="uploadFiles(this.files)">
            </div>

            <!-- Progress Bar -->
            <div class="progress-container" id="progressBox">
                <div class="progress-bar" id="progressBar"></div>
                <div class="progress-text" id="progressText">UPLOADING... 0%</div>
            </div>

            <!-- Action Bar & View Switcher -->
            <div class="action-row">
                <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                    <form action="{{ url_for('create_folder') }}" method="post" style="display: flex; gap: 6px;">
                        <input type="hidden" name="subpath" value="{{ current_dir }}">
                        <input type="text" name="foldername" placeholder="New Folder Name..." class="input-text" required>
                        <button type="submit" class="btn"><i class="fa-solid fa-folder-plus"></i> MKDIR</button>
                    </form>
                    <button onclick="deleteSelected()" class="btn btn-danger"><i class="fa-solid fa-trash"></i> DELETE</button>
                </div>

                <div class="view-switchers">
                    <button class="view-btn active" id="btnGrid" onclick="setViewMode('grid')"><i class="fa-solid fa-border-all"></i> Grid</button>
                    <button class="view-btn" id="btnList" onclick="setViewMode('list')"><i class="fa-solid fa-list"></i> List</button>
                </div>
            </div>

            <!-- File Content Area -->
            <div class="content-area">
                <div class="view-grid" id="fileContainer">
                    {% for item in items %}
                        {% set item_path = (current_dir + '/' + item.name) if current_dir else item.name %}
                        <div class="file-card">
                            <input type="checkbox" class="card-select file-checkbox" value="{{ item_path }}">
                            
                            {% if item.is_dir %}
                                <a href="{{ url_for('index', subpath=item_path) }}" class="card-preview">
                                    <i class="fa-solid fa-folder folder-icon"></i>
                                </a>
                                <div class="card-info">
                                    <a href="{{ url_for('index', subpath=item_path) }}" class="card-title" style="color:#ff6600;">{{ item.name }}/</a>
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
                        <div style="grid-column: 1 / -1; text-align: center; color: #ff0055; padding: 40px; font-weight: bold;">
                            [NO FILES OR DIRECTORY IS EMPTY]
                        </div>
                    {% endfor %}
                </div>
            </div>
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

        function setViewMode(mode) {
            const container = document.getElementById('fileContainer');
            const btnGrid = document.getElementById('btnGrid');
            const btnList = document.getElementById('btnList');

            if (mode === 'list') {
                container.className = 'view-list';
                btnList.classList.add('active');
                btnGrid.classList.remove('active');
                localStorage.setItem('pref_view_mode', 'list');
            } else {
                container.className = 'view-grid';
                btnGrid.classList.add('active');
                btnList.classList.remove('active');
                localStorage.setItem('pref_view_mode', 'grid');
            }
        }

        document.addEventListener("DOMContentLoaded", () => {
            const savedMode = localStorage.getItem('pref_view_mode') || 'grid';
            setViewMode(savedMode);
            imgList = Array.from(document.querySelectorAll('.img-item')).map(img => img.src);
        });

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
                    progressText.innerText = `UPLOADING ${files.length} FILE(S)... ${percent}%`;
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

        let imgList = [];
        let currentIndex = 0;

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
@app.route('/dir/<path:subpath>')
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
            
    return redirect(url_for('index', subpath=subpath) if subpath else url_for('index'))

@app.route('/create_folder', methods=['POST'])
def create_folder():
    subpath = request.form.get('subpath', '')
    foldername = request.form.get('foldername', '').strip()
    if foldername:
        prefix = get_prefix(subpath)
        key = f"{prefix}{foldername}/.keep"
        s3_client.put_object(Bucket=BUCKET_NAME, Key=key, Body=b'')
    return redirect(url_for('index', subpath=subpath) if subpath else url_for('index'))

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

    return redirect(url_for('index', subpath=subpath) if subpath else url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

