import os
import mimetypes
import boto3
from botocore.config import Config
from flask import Flask, request, redirect, url_for, render_template_string, Response, jsonify

app = Flask(__name__)

# ตั้งค่า Max Request Size เป็น 500MB
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

ACCOUNT_ID = os.environ.get('CF_ACCOUNT_ID')
ACCESS_KEY = os.environ.get('CF_ACCESS_KEY')
SECRET_KEY = os.environ.get('CF_SECRET_KEY')
BUCKET_NAME = os.environ.get('CF_BUCKET_NAME', 'my-files')

# Config Boto3 ป้องกัน Timeout
r2_config = Config(
    retries=dict(max_attempts=10),
    connect_timeout=120,
    read_timeout=120
)

s3_client = None
if ACCOUNT_ID and ACCESS_KEY and SECRET_KEY:
    s3_client = boto3.client(
        's3',
        endpoint_url=f'https://{ACCOUNT_ID}.r2.cloudflarestorage.com',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name='auto',
        config=r2_config
    )

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>R2 CYBER_VAULT</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * { box-sizing: border-box; font-family: 'Consolas', 'Courier New', monospace; }
        html, body { height: 100%; margin: 0; padding: 0; background-color: #030308; color: #00ff66; overflow-x: hidden; }
        
        .page-wrapper { min-height: 100vh; padding: 8px; display: flex; flex-direction: column; background: radial-gradient(circle at center, #0a0a16 0%, #020205 100%); }
        
        /* แก้ปัญหากรอบล้นขอบจอด้วย max-width และ overflow-x hidden */
        .container { 
            flex: 1; 
            max-width: 100%; 
            width: 100%; 
            margin: 0 auto; 
            background: rgba(10, 10, 20, 0.95); 
            border: 2px solid #00ff66 !important; 
            border-radius: 8px; 
            padding: 10px; 
            box-shadow: 0 0 15px rgba(0, 255, 102, 0.5), inset 0 0 10px rgba(0, 255, 102, 0.1) !important; 
            display: flex; 
            flex-direction: column; 
            overflow: hidden;
        }
        
        /* Header ปรับแต่งรองรับจอมือถือ ไม่ให้ดันกรอบล้น */
        .header { 
            border-bottom: 2px solid #ff0055; 
            padding-bottom: 8px; 
            margin-bottom: 10px; 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            flex-wrap: wrap;
            gap: 6px;
            width: 100%;
        }
        .header h1 { margin: 0; font-size: 1rem; color: #00f0ff; text-shadow: 0 0 6px #00f0ff; display: flex; align-items: center; gap: 6px; }
        
        .status-container { font-size: 0.75rem; color: #00f0ff; white-space: nowrap; }
        .status-online { color: #00ff66; font-weight: bold; text-shadow: 0 0 6px #00ff66; animation: blinker 1s cubic-bezier(0.5, 0, 1, 1) infinite alternate; }
        @keyframes blinker { from { opacity: 1.0; } to { opacity: 0.15; } }

        /* Path Bar */
        .nav-bar { display: flex; align-items: center; gap: 8px; background: #080812; padding: 8px; border-radius: 6px; border: 1px solid #ff6600; margin-bottom: 10px; flex-wrap: wrap; }
        .nav-btn { background: #1a0033; color: #ff0055; border: 1px solid #ff0055; padding: 4px 8px; border-radius: 4px; cursor: pointer; text-decoration: none; font-size: 0.75rem; font-weight: bold; }
        .nav-btn:hover { background: #ff0055; color: #fff; }
        .path-display { font-size: 0.8rem; color: #00f0ff; word-break: break-all; flex-grow: 1; }

        /* Drop Zone */
        .drop-zone { border: 2px dashed #00f0ff; background: rgba(0, 240, 255, 0.03); border-radius: 6px; padding: 15px 8px; text-align: center; cursor: pointer; margin-bottom: 10px; }
        .drop-zone:hover { background: rgba(0, 240, 255, 0.1); border-color: #ff0055; }
        .drop-zone i { font-size: 1.5rem; margin-bottom: 4px; color: #00f0ff; }

        /* Actions Bar */
        .action-row { display: flex; gap: 6px; margin-bottom: 10px; flex-wrap: wrap; justify-content: space-between; align-items: center; }
        .input-text { background: #000; border: 1px solid #bd00ff; color: #00f0ff; padding: 6px; border-radius: 4px; font-size: 0.75rem; outline: none; width: 130px; }
        
        .btn { background: #0d001a; border: 1px solid #bd00ff; color: #bd00ff; padding: 6px 10px; border-radius: 4px; cursor: pointer; font-size: 0.75rem; font-weight: bold; display: inline-flex; align-items: center; gap: 4px; }
        .btn-select { border-color: #00ff66; color: #00ff66; background: #001a0d; }
        .btn-danger { border-color: #ff0055; color: #ff0055; background: #1a000d; }

        /* Progress Bar */
        .progress-container { display: none; margin-bottom: 10px; background: #000; border: 1px solid #00ff66; border-radius: 4px; position: relative; height: 22px; overflow: hidden; }
        .progress-bar { width: 0%; height: 100%; background: linear-gradient(90deg, #00ff66, #00f0ff); transition: width 0.1s; }
        .progress-text { position: absolute; width: 100%; text-align: center; font-size: 0.75rem; color: #fff; font-weight: bold; line-height: 20px; top: 0; left: 0; text-shadow: 0 0 3px #000; }

        /* View Switcher */
        .view-switchers { display: flex; gap: 2px; background: #000; border: 1px solid #ff6600; border-radius: 4px; padding: 2px; }
        .view-btn { background: transparent; border: none; color: #ff6600; padding: 4px 8px; cursor: pointer; border-radius: 2px; font-weight: bold; font-size: 0.75rem; }
        .view-btn.active { background: #ff6600; color: #000; }

        /* Content Area Container */
        .content-area { flex: 1; border: 1px solid #00ff66; border-radius: 6px; padding: 8px; background: rgba(3, 3, 10, 0.8); min-height: 250px; }

        /* GRID MODE (2 คอลัมน์สำหรับมือถือ) */
        .view-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
        @media (min-width: 600px) { .view-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); } }
        
        .view-grid .file-card { background: #060612; border: 1px solid #bd00ff; border-radius: 4px; padding: 6px; position: relative; display: flex; flex-direction: column; justify-content: space-between; height: 150px; }
        .view-grid .card-preview { height: 80px; display: flex; align-items: center; justify-content: center; cursor: pointer; overflow: hidden; margin-top: 8px; }
        .view-grid .card-preview img { max-width: 100%; max-height: 100%; object-fit: cover; border-radius: 3px; }
        .view-grid .card-preview i { font-size: 2rem; color: #00f0ff; }
        .view-grid .folder-icon { color: #ff6600 !important; }
        .view-grid .card-info { text-align: center; margin-top: 2px; }
        .view-grid .card-title { font-size: 0.7rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; color: #00ff66; text-decoration: none; }
        .view-grid .card-actions { display: flex; justify-content: center; gap: 8px; margin-top: 2px; }

        /* LIST MODE */
        .view-list { display: flex; flex-direction: column; gap: 4px; }
        .view-list .file-card { background: #060612; border: 1px solid #330066; border-radius: 4px; padding: 6px 10px; display: flex; align-items: center; gap: 8px; justify-content: space-between; }
        .view-list .card-preview { width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; }
        .view-list .card-preview img { width: 28px; height: 28px; object-fit: cover; border-radius: 2px; }
        .view-list .card-preview i { font-size: 1.1rem; color: #00f0ff; }
        .view-list .folder-icon { color: #ff6600 !important; }
        .view-list .card-info { flex-grow: 1; overflow: hidden; }
        .view-list .card-title { font-size: 0.75rem; color: #00ff66; text-decoration: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; }
        .view-list .card-actions { display: flex; gap: 8px; align-items: center; }

        .card-select { cursor: pointer; accent-color: #ff0055; }
        .icon-btn { background: transparent; border: none; color: #00f0ff; cursor: pointer; font-size: 0.85rem; padding: 2px; }
        .icon-btn-del { color: #ff0055; }

        /* Lightbox */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.92); z-index: 1000; justify-content: center; align-items: center; }
        .modal-content { max-width: 95%; max-height: 85%; object-fit: contain; border: 1px solid #00f0ff; }
        .modal-nav { position: absolute; top: 50%; transform: translateY(-50%); font-size: 2rem; color: #00f0ff; cursor: pointer; padding: 10px; background: rgba(0,0,0,0.5); user-select: none; }
        .modal-prev { left: 10px; }
        .modal-next { right: 10px; }
        .modal-close { position: absolute; top: 10px; right: 20px; font-size: 2rem; color: #ff0055; cursor: pointer; }
    </style>
</head>
<body>
    <div class="page-wrapper">
        <div class="container">
            <div class="header">
                <h1><i class="fa-solid fa-microchip"></i> R2_CYBER_VAULT</h1>
                <div class="status-container">
                    SYSTEM_STATUS: <span class="status-online">● ONLINE</span>
                </div>
            </div>

            <!-- Path Bar -->
            <div class="nav-bar">
                {% if parent_dir is not none %}
                    {% if parent_dir == '' %}
                        <a href="{{ url_for('index') }}" class="nav-btn"><i class="fa-solid fa-arrow-left"></i> BACK</a>
                    {% else %}
                        <a href="{{ url_for('index_dir', subpath=parent_dir) }}" class="nav-btn"><i class="fa-solid fa-arrow-left"></i> BACK</a>
                    {% endif %}
                {% endif %}
                <a href="{{ url_for('index') }}" class="nav-btn"><i class="fa-solid fa-house"></i> ROOT</a>
                <div class="path-display">PATH: /{{ current_dir }}</div>
            </div>

            <!-- Drop Zone -->
            <div class="drop-zone" id="dropZone" onclick="document.getElementById('fileInput').click();">
                <i class="fa-solid fa-cloud-arrow-up"></i>
                <div><strong>CLICK / DROP FILES HERE</strong></div>
                <div style="font-size: 0.7rem; color: #ff6600; margin-top: 2px;">TARGET_DIR: /{{ current_dir if current_dir else 'ROOT' }}</div>
                <input type="file" id="fileInput" multiple style="display: none;" onchange="uploadQueue(this.files)">
            </div>

            <!-- Progress Bar -->
            <div class="progress-container" id="progressBox">
                <div class="progress-bar" id="progressBar"></div>
                <div class="progress-text" id="progressText">UPLOADING... 0%</div>
            </div>

            <!-- Action Bar -->
            <div class="action-row">
                <div style="display: flex; gap: 4px; flex-wrap: wrap;">
                    <form action="{{ url_for('create_folder') }}" method="post" style="display: flex; gap: 4px;">
                        <input type="hidden" name="subpath" value="{{ current_dir }}">
                        <input type="text" name="foldername" placeholder="Folder Name..." class="input-text" required>
                        <button type="submit" class="btn"><i class="fa-solid fa-folder-plus"></i> MKDIR</button>
                    </form>
                    <button onclick="toggleSelectAll()" class="btn btn-select" id="btnSelectAll"><i class="fa-solid fa-check-double"></i> SELECT ALL</button>
                    <button onclick="deleteSelected()" class="btn btn-danger"><i class="fa-solid fa-trash"></i> DELETE</button>
                </div>

                <div class="view-switchers">
                    <button class="view-btn active" id="btnGrid" onclick="setViewMode('grid')"><i class="fa-solid fa-border-all"></i> Grid</button>
                    <button class="view-btn" id="btnList" onclick="setViewMode('list')"><i class="fa-solid fa-list"></i> List</button>
                </div>
            </div>

            <!-- Content Area -->
            <div class="content-area">
                <div class="view-grid" id="fileContainer">
                    {% for item in items %}
                        {% set item_path = (current_dir + '/' + item.name) if current_dir else item.name %}
                        <div class="file-card">
                            <input type="checkbox" class="card-select file-checkbox" value="{{ item_path }}">
                            
                            {% if item.is_dir %}
                                <a href="{{ url_for('index_dir', subpath=item_path) }}" class="card-preview">
                                    <i class="fa-solid fa-folder folder-icon"></i>
                                </a>
                                <div class="card-info">
                                    <a href="{{ url_for('index_dir', subpath=item_path) }}" class="card-title" style="color:#ff6600;">{{ item.name }}/</a>
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
                        <div style="grid-column: 1 / -1; text-align: center; color: #ff0055; padding: 30px; font-weight: bold; font-size: 0.85rem;">
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
        let isAllSelected = false;

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

        function toggleSelectAll() {
            const checkboxes = document.querySelectorAll('.file-checkbox');
            isAllSelected = !isAllSelected;
            checkboxes.forEach(cb => cb.checked = isAllSelected);
            
            const btn = document.getElementById('btnSelectAll');
            if (isAllSelected) {
                btn.innerHTML = '<i class="fa-solid fa-xmark"></i> UNSELECT ALL';
            } else {
                btn.innerHTML = '<i class="fa-solid fa-check-double"></i> SELECT ALL';
            }
        }

        document.addEventListener("DOMContentLoaded", () => {
            const savedMode = localStorage.getItem('pref_view_mode') || 'grid';
            setViewMode(savedMode);
            imgList = Array.from(document.querySelectorAll('.img-item')).map(img => img.src);
        });

        const dropZone = document.getElementById('dropZone');
        ['dragenter', 'dragover'].forEach(name => {
            dropZone.addEventListener(name, (e) => { e.preventDefault(); }, false);
        });
        ['dragleave', 'drop'].forEach(name => {
            dropZone.addEventListener(name, (e) => { e.preventDefault(); }, false);
        });
        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            uploadQueue(dt.files);
        });

        async function uploadQueue(files) {
            if (files.length === 0) return;

            const progressBox = document.getElementById('progressBox');
            const progressBar = document.getElementById('progressBar');
            const progressText = document.getElementById('progressText');

            progressBox.style.display = 'block';

            let totalFiles = files.length;
            let successCount = 0;

            for (let i = 0; i < totalFiles; i++) {
                let file = files[i];
                let formData = new FormData();
                formData.append('subpath', currentSubpath);
                formData.append('file', file);

                progressText.innerText = `UPLOADING (${i + 1}/${totalFiles}): ${file.name}...`;
                
                try {
                    let response = await fetch('{{ url_for("upload_single") }}', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (response.ok) {
                        successCount++;
                        let percent = Math.round(((i + 1) / totalFiles) * 100);
                        progressBar.style.width = percent + '%';
                    }
                } catch (err) {
                    console.error('Upload Error', err);
                }
            }

            progressText.innerText = `DONE! (${successCount}/${totalFiles})`;
            setTimeout(() => { window.location.reload(); }, 600);
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
def index():
    return render_index("")

@app.route('/dir/<path:subpath>')
def index_dir(subpath=""):
    return render_index(subpath)

def render_index(subpath=""):
    if not s3_client:
        return "[SYSTEM_ERROR] MISSING_R2_CREDENTIALS"
    
    subpath = subpath.strip("/")
    prefix = get_prefix(subpath)
    
    parent_dir = None
    if subpath:
        if '/' in subpath:
            parent_dir = subpath.rsplit('/', 1)[0]
        else:
            parent_dir = ''
            
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
            
    return render_template_string(HTML_TEMPLATE, items=items, current_dir=subpath, parent_dir=parent_dir)

@app.route('/upload_single', methods=['POST'])
def upload_single():
    subpath = request.form.get('subpath', '').strip("/")
    prefix = get_prefix(subpath)
    file = request.files.get('file')
    
    if file and file.filename != '':
        key = f"{prefix}{file.filename}"
        mime_type, _ = mimetypes.guess_type(file.filename)
        extra_args = {'ContentType': mime_type} if mime_type else {}
        try:
            s3_client.upload_fileobj(file, BUCKET_NAME, key, ExtraArgs=extra_args)
            return jsonify({'status': 'success'}), 200
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
            
    return jsonify({'status': 'invalid'}), 400

@app.route('/create_folder', methods=['POST'])
def create_folder():
    subpath = request.form.get('subpath', '').strip("/")
    foldername = request.form.get('foldername', '').strip()
    if foldername:
        prefix = get_prefix(subpath)
        key = f"{prefix}{foldername}/.keep"
        s3_client.put_object(Bucket=BUCKET_NAME, Key=key, Body=b'')
    return redirect(url_for('index_dir', subpath=subpath) if subpath else url_for('index'))

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

    return redirect(url_for('index_dir', subpath=subpath) if subpath else url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

