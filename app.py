import os
import boto3
from flask import Flask, request, redirect, url_for, render_template_string, Response

app = Flask(__name__)

# ดึงค่าการเชื่อมต่อ Cloudflare R2 จาก Environment Variables
ACCOUNT_ID = os.environ.get('CF_ACCOUNT_ID')
ACCESS_KEY = os.environ.get('CF_ACCESS_KEY')
SECRET_KEY = os.environ.get('CF_SECRET_KEY')
BUCKET_NAME = os.environ.get('CF_BUCKET_NAME', 'ไฟล์ของฉัน')

# เชื่อมต่อ Cloudflare R2 ผ่าน S3 Protocol
s3_client = boto3.client(
    's3',
    endpoint_url=f'https://{ACCOUNT_ID}.r2.cloudflarestorage.com',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    region_name='auto'
) if ACCOUNT_ID else None

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cloud Private Storage</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 16px; background-color: #f4f6f8; color: #333; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
        h2 { margin-top: 0; font-size: 1.2rem; color: #111; }
        .form-group { margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 15px; }
        input[type="file"], input[type="text"] { width: 100%; padding: 10px; margin-top: 5px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 8px; }
        button { background-color: #007aff; color: white; border: none; padding: 10px 15px; border-radius: 8px; font-weight: bold; width: 100%; margin-top: 8px; cursor: pointer; }
        button.create-btn { background-color: #34c759; }
        .file-list { list-style: none; padding: 0; margin-top: 20px; }
        .file-item { display: flex; align-items: center; justify-content: space-between; padding: 12px; background: #f9f9f9; margin-bottom: 8px; border-radius: 8px; user-select: none; -webkit-user-select: none; }
        .file-item a { text-decoration: none; color: #007aff; font-weight: 500; word-break: break-all; }
        .folder-link { color: #ff9500 !important; font-weight: bold !important; }
        .breadcrumb { margin-bottom: 15px; font-size: 0.9rem; }
        .breadcrumb a { color: #007aff; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <h2>☁️ Cloud Storage (R2 Permanent)</h2>
        
        <div class="breadcrumb">
            <a href="{{ url_for('index') }}">หน้าแรก</a>
            {% if current_dir %}
                / {{ current_dir }}
            {% endif %}
        </div>

        <div class="form-group">
            <form action="{{ url_for('upload_file') }}" method="post" enctype="multipart/form-data">
                <input type="hidden" name="subpath" value="{{ current_dir }}">
                <input type="file" name="file" required>
                <button type="submit">⬆️ อัปโหลดไฟล์ถาวรไป Cloud</button>
            </form>
        </div>

        <div class="form-group">
            <form action="{{ url_for('create_folder') }}" method="post">
                <input type="hidden" name="subpath" value="{{ current_dir }}">
                <input type="text" name="foldername" placeholder="ชื่อโฟลเดอร์ใหม่..." required>
                <button type="submit" class="create-btn">📁 สร้างโฟลเดอร์</button>
            </form>
        </div>

        <h3>รายการไฟล์ใน Cloud</h3>
        <p style="font-size: 0.8rem; color: #888;">💡 กดค้างที่รายการเพื่อลบออกจาก Cloud</p>
        <ul class="file-list">
            {% for item in items %}
                <li class="file-item" onmousedown="startPress('{{ item.name }}', {{ 'true' if item.is_dir else 'false' }})" onmouseup="cancelPress()" onmouseleave="cancelPress()" ontouchstart="startPress('{{ item.name }}', {{ 'true' if item.is_dir else 'false' }})" ontouchend="cancelPress()">
                    {% if item.is_dir %}
                        <a href="{{ url_for('index', subpath=(current_dir + '/' + item.name) if current_dir else item.name) }}" class="folder-link">📁 {{ item.name }}</a>
                    {% else %}
                        <a href="{{ url_for('download_file', filename=(current_dir + '/' + item.name) if current_dir else item.name) }}" target="_blank">📄 {{ item.name }}</a>
                    {% endif %}
                </li>
            {% else %}
                <li style="color: #999; text-align: center; padding: 20px;">ไม่มีไฟล์ในระบบ Cloud</li>
            {% endfor %}
        </ul>
    </div>

    <script>
        let pressTimer;
        function startPress(name, isDir) {
            pressTimer = setTimeout(() => {
                const typeStr = isDir ? 'โฟลเดอร์' : 'ไฟล์';
                if (confirm(`คุณต้องการลบ ${typeStr} "${name}" จาก Cloud ใช่หรือไม่?`)) {
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

        function cancelPress() {
            clearTimeout(pressTimer);
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
        return "กรุณาตั้งค่า Environment Variables ใน Render ก่อนใช้งาน"
    
    prefix = get_prefix(subpath)
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix, Delimiter='/')
    
    items = []
    # เพิ่มโฟลเดอร์
    for p in response.get('CommonPrefixes', []):
        folder_name = p['Prefix'][len(prefix):].strip('/')
        if folder_name:
            items.append({'name': folder_name, 'is_dir': True})
            
    # เพิ่มไฟล์
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
        headers={"Content-Disposition": f"attachment; filename={os.path.basename(filename)}"}
    )

@app.route('/delete', methods=['POST'])
def delete_item():
    item_path = request.form.get('item_path', '').strip('/')
    
    # ดึงรายการภายใต้เส้นทางที่ต้องการลบ
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=item_path)
    if 'Contents' in response:
        delete_keys = [{'Key': obj['Key']} for obj in response['Contents']]
        s3_client.delete_objects(Bucket=BUCKET_NAME, Delete={'Objects': delete_keys})
        
    parent_dir = os.path.dirname(item_path)
    return redirect(url_for('index', subpath=parent_dir))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
