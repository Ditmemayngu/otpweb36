from flask import Flask, request, redirect, url_for, render_template_string, session, jsonify
import requests, re, random, os, json

APP_SECRET = os.environ.get('APP_SECRET', 'change_this_secret')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
DOMAINS_FILE = 'domains.json'
API_MAILBOX = 'https://api.catchmail.io/api/v1/mailbox'
API_MESSAGE = 'https://api.catchmail.io/api/v1/message/{}'

DEFAULT_DOMAINS = [
    'vua36.online', 'sena36.online', 'paris36.site', 'hanoi36.shop',
    'quynhon36.store', 'todoi36.online', 'thanhhoa.store', 'thanhhoa.fun',
    'shop36.online', 'shop36.site', 'shopthanhhoa.online'
]

HO = ['nguyen','tran','le','pham','hoang','huynh','phan','vu','vo','dang','bui','do','ho','ngo','duong','ly']
TEN_DEM = ['van','minh','quang','duc','gia','thanh','tuan','bao','anh','nhat','hoai','trung','ngoc','huu']
TEN = ['anh','hieu','huy','long','nam','phuc','khang','dat','son','duy','tuan','phong','linh','trang','vy','ngan','thao','han','nhi','my']

app = Flask(__name__)
app.secret_key = APP_SECRET


def load_domains():
    if not os.path.exists(DOMAINS_FILE):
        return DEFAULT_DOMAINS
    try:
        with open(DOMAINS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) and data else DEFAULT_DOMAINS
    except Exception:
        return DEFAULT_DOMAINS


def clean_domain(domain):
    return domain.strip().lower().replace('https://','').replace('http://','').replace('/','')


def email_domain(email):
    return email.split('@')[-1].lower().strip() if '@' in email else ''


def is_allowed_domain(email):
    return email_domain(email) in load_domains()


def random_email(domain):
    name = f"{random.choice(HO)}{random.choice(TEN_DEM)}{random.choice(TEN)}{random.randint(1000,9999)}"
    return f'{name}@{domain}'


def generate_two_cross_domain():
    domains = load_domains()
    if len(domains) < 2:
        return None, 'Cần ít nhất 2 domain để tạo 2 email không trùng domain.'
    selected = random.sample(domains, 2)
    return [{'domain': d, 'email': random_email(d)} for d in selected], None


def get_body(msg):
    body = msg.get('body', '')
    if isinstance(body, dict):
        return body.get('text', '') or body.get('html', '') or str(body)
    return str(body)


def find_otp(text):
    m6 = re.findall(r'\b\d{6}\b', text)
    if m6:
        return m6[0]
    m = re.findall(r'\b\d{4,8}\b', text)
    return m[0] if m else None


def get_mailbox(email):
    res = requests.get(API_MAILBOX, params={'address': email}, timeout=10)
    data = res.json()
    return data.get('messages', []), data.get('count', 0)


def get_message(email, msg_id):
    msg = requests.get(API_MESSAGE.format(msg_id), params={'mailbox': email}, timeout=10).json()
    body = get_body(msg)
    msg['_body_text'] = body
    msg['_otp'] = find_otp(body)
    return msg


def build_inbox_data(email):
    try:
        messages, count = get_mailbox(email)
        selected_id = messages[0].get('id') if messages else None
        selected_message = get_message(email, selected_id) if selected_id else None
        return {'email': email, 'messages': messages, 'count': count, 'selected_id': selected_id, 'selected_message': selected_message, 'error': None}
    except Exception as e:
        return {'email': email, 'messages': [], 'count': 0, 'selected_id': None, 'selected_message': None, 'error': str(e)}

HTML = r'''
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>CatchMail Realtime Inbox Tool</title>
<style>
*{box-sizing:border-box}body{font-family:Arial,sans-serif;max-width:1180px;margin:24px auto;padding:0 16px;background:#fafafa;color:#111}input,button{padding:10px;font-size:15px}button{cursor:pointer;border:1px solid #bbb;background:white;border-radius:5px}button:hover{background:#f2f2f2}.box{border:1px solid #ddd;border-radius:10px;padding:16px;margin:16px 0;background:white}.admin-only{border-color:#c6a700;background:#fffdf0}.error{color:#b00020;font-weight:bold}.ok{color:green;font-weight:bold}.small{color:#666;font-size:13px}.otp{font-size:26px;font-weight:bold;color:#d00}.input-row{display:flex;gap:8px}.input-row input{flex:1}.generated-table{width:100%;border-collapse:collapse;margin-top:10px}.generated-table th,.generated-table td{border:1px solid #ddd;padding:10px}.generated-table th{background:#f1f1f1}.generated-email{font-weight:bold}.notice{border:1px solid #d8d8d8;background:white;padding:14px;border-radius:10px;margin:14px 0}.inline-inbox-section{margin-top:18px}.inbox-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start}.mailbox-card{border:1px solid #d8d8d8;border-radius:10px;background:#fff;overflow:hidden}.mailbox-top{text-align:center;padding:16px;border-bottom:1px solid #ddd;background:#fbfbfb}.email-line{display:flex;justify-content:center;align-items:center;margin:8px 0}.email-box{border:1px solid #ccc;padding:10px;min-width:300px;font-weight:bold;background:white;overflow-wrap:anywhere}.refresh-line{display:flex;justify-content:center;gap:10px;align-items:center;margin-top:8px}.live-dot{display:inline-block;width:9px;height:9px;background:#00b894;border-radius:50%;margin-right:5px}.inbox-wrap{display:grid;grid-template-columns:38% 62%;min-height:330px}.inbox-list{border-right:1px solid #ddd;max-height:420px;overflow-y:auto}.inbox-title{padding:10px;border-bottom:1px solid #ddd;font-size:18px;background:#fff;position:sticky;top:0}.message-item{display:block;padding:10px;border-bottom:1px solid #eee;color:#111;text-decoration:none;cursor:pointer}.message-item:hover{background:#f5f5f5}.message-item.active{background:#eef5ff}.subject{font-weight:bold;font-size:15px;margin-bottom:4px}.from{color:#06c;font-size:13px;margin-bottom:4px;overflow-wrap:anywhere}.snippet{color:#555;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.message-view{padding:12px;max-height:420px;overflow-y:auto}.message-head{border-bottom:1px solid #ddd;padding-bottom:10px;margin-bottom:10px}.message-head h3{margin-top:0}.body-box{border:1px solid #ddd;padding:10px;min-height:150px;white-space:pre-wrap;overflow-wrap:anywhere;background:#fff;font-size:13px}@media(max-width:980px){.inbox-grid{grid-template-columns:1fr}}@media(max-width:700px){.input-row{flex-direction:column}.inbox-wrap{grid-template-columns:1fr}.inbox-list{border-right:0;border-bottom:1px solid #ddd}}
</style>
</head>
<body>
<h2>🚀 CatchMail Realtime Inbox Tool</h2>
<div class="box">
<h3>🔍 Người dùng: nhập full email để xem inbox / OTP</h3>
<form method="GET" action="/inbox" class="input-row">
<input type="text" name="email" placeholder="Ví dụ: nguyenvananh1234@thanhhoa.store" value="{{ inbox_email or '' }}" required>
<button type="submit">Mở inbox</button>
</form>
{% if error %}<p class="error">{{ error }}</p>{% endif %}
</div>
{% if inbox_email and not error %}{{ render_inbox_card(single_inbox)|safe }}{% endif %}
<div class="box admin-only">
<h3>🔐 Admin</h3>
{% if admin %}
<p class="ok">Đang đăng nhập admin.</p>
<h4>🎲 Tạo 2 email random xen kẽ domain</h4>
<p class="small">Mỗi lần tạo lấy 2 domain khác nhau trong danh sách, không trùng nhau.</p>
<form method="POST" action="/generate"><button type="submit">Tạo 2 email random</button></form>
{% if generate_error %}<p class="error">{{ generate_error }}</p>{% endif %}
{% if generated_emails %}
<div class="notice">
<h4>✅ Bảng thông báo email vừa tạo</h4>
<table class="generated-table"><thead><tr><th>#</th><th>Domain</th><th>Email</th><th>Copy</th></tr></thead><tbody>
{% for item in generated_emails %}<tr><td>{{ loop.index }}</td><td>{{ item.domain }}</td><td class="generated-email">{{ item.email }}</td><td><button onclick="copyText('{{ item.email }}')">Copy</button></td></tr>{% endfor %}
</tbody></table>
<div class="inline-inbox-section"><h4>📬 Inbox realtime tự hiện cho 2 email vừa tạo</h4><div class="inbox-grid">{% for inbox in generated_inboxes %}{{ render_inbox_card(inbox)|safe }}{% endfor %}</div></div>
</div>
{% endif %}
<hr>
<h4>➕ Domain</h4>
<p class="small">Trên Vercel, thêm/xóa domain bằng web có thể không lưu bền. Ổn định nhất là sửa domains.json trên GitHub.</p>
<p>Domain hiện có:</p>
<table class="generated-table"><thead><tr><th>#</th><th>Domain</th></tr></thead><tbody>{% for d in domains %}<tr><td>{{ loop.index }}</td><td><b>{{ d }}</b></td></tr>{% endfor %}</tbody></table>
<form method="POST" action="/logout"><button type="submit">Đăng xuất admin</button></form>
{% else %}
<p class="small">Chỉ admin mới tạo email random.</p>
<form method="POST" action="/admin-login" class="input-row"><input type="password" name="password" placeholder="Mật khẩu admin"><button type="submit">Đăng nhập admin</button></form>
{% endif %}
</div>
<p class="small">Tool chỉ đọc được email thuộc domain đã trỏ MX về CatchMail.</p>
<script>
const POLL_INTERVAL_MS=3000;
function copyText(t){navigator.clipboard.writeText(t)}
function esc(t){if(t===null||t===undefined)return '';return String(t).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}
async function fetchJson(url){const r=await fetch(url,{cache:'no-store'});return await r.json()}
function itemHtml(msg,activeId){const a=msg.id===activeId?'active':'';return `<div class="message-item ${a}" data-message-id="${esc(msg.id)}"><div class="subject">${esc(msg.subject||'(No subject)')}</div><div class="from">${esc(msg.from||'')}</div><div class="snippet">${esc(msg.date||'')} · Size: ${esc(msg.size||'')}</div></div>`}
function emptyView(){return `<h3>Chưa có mail</h3><p>Email này chưa nhận được mail nào.</p>`}
function viewHtml(msg){if(!msg)return emptyView();let otp='';if(msg.otp){otp=`<p>OTP:</p><p class="otp">${esc(msg.otp)}</p><button onclick="copyText('${esc(msg.otp)}')">Copy OTP</button>`}return `<div class="message-head"><h3>${esc(msg.subject||'(No subject)')}</h3><p><b>From:</b> ${esc(msg.from||'')}</p><p><b>Date:</b> ${esc(msg.date||'')}</p>${otp}</div><h4>Nội dung mail</h4><div class="body-box">${esc(msg.body||'')}</div>`}
async function loadMessage(card,msgId){const email=card.dataset.email;const view=card.querySelector('.message-view');view.innerHTML='<p>Đang tải mail...</p>';const data=await fetchJson(`/api/message?email=${encodeURIComponent(email)}&id=${encodeURIComponent(msgId)}`);if(!data.ok){view.innerHTML=`<p class="error">${esc(data.error||'Lỗi tải mail')}</p>`;return}card.dataset.selectedId=msgId;view.innerHTML=viewHtml(data.message);card.querySelectorAll('.message-item').forEach(i=>i.classList.toggle('active',i.dataset.messageId===msgId))}
async function refreshCard(card,keepSelected=true){const email=card.dataset.email;const list=card.querySelector('.message-list-body');const count=card.querySelector('.message-count');try{const data=await fetchJson(`/api/mailbox?email=${encodeURIComponent(email)}`);if(!data.ok){list.innerHTML=`<div style="padding:14px" class="error">${esc(data.error||'Lỗi tải inbox')}</div>`;return}count.textContent=data.count;if(!data.messages.length){list.innerHTML='<div style="padding:14px">❌ Chưa có mail nào.</div>';card.querySelector('.message-view').innerHTML=emptyView();return}const ids=data.messages.map(m=>m.id);let selected=(keepSelected&&ids.includes(card.dataset.selectedId))?card.dataset.selectedId:data.messages[0].id;list.innerHTML=data.messages.map(m=>itemHtml(m,selected)).join('');list.querySelectorAll('.message-item').forEach(i=>i.addEventListener('click',()=>loadMessage(card,i.dataset.messageId)));if(card.dataset.selectedId!==selected){await loadMessage(card,selected)}}catch(e){list.innerHTML=`<div style="padding:14px" class="error">Lỗi realtime: ${esc(e)}</div>`}}
function setupRealtime(){document.querySelectorAll('.mailbox-card[data-email]').forEach(card=>{card.querySelectorAll('.message-item').forEach(i=>i.addEventListener('click',()=>loadMessage(card,i.dataset.messageId)));refreshCard(card,true);setInterval(()=>refreshCard(card,true),POLL_INTERVAL_MS)})}
document.addEventListener('DOMContentLoaded',setupRealtime);
</script>
</body>
</html>
'''

INBOX_CARD = r'''
<div class="mailbox-card" data-email="{{ inbox.email }}" data-selected-id="{{ inbox.selected_id or '' }}">
<div class="mailbox-top">
<div class="small">Your temporary email address</div>
<div class="email-line"><div class="email-box">{{ inbox.email }}</div><button onclick="copyText('{{ inbox.email }}')">📋 Copy</button></div>
<div class="refresh-line"><span class="small"><span class="live-dot"></span>Realtime mỗi 3 giây</span><button type="button" onclick="refreshCard(this.closest('.mailbox-card'), false)">⟳ Refresh ngay</button></div>
{% if inbox.error %}<p class="error">Lỗi: {{ inbox.error }}</p>{% endif %}
</div>
<div class="inbox-wrap">
<div class="inbox-list"><div class="inbox-title">Inbox <span class="small">(<span class="message-count">{{ inbox.count }}</span>)</span></div><div class="message-list-body">
{% if not inbox.messages %}<div style="padding:14px">❌ Chưa có mail nào.</div>{% endif %}
{% for m in inbox.messages %}<div class="message-item {% if inbox.selected_id == m.id %}active{% endif %}" data-message-id="{{ m.id }}"><div class="subject">{{ m.subject or '(No subject)' }}</div><div class="from">{{ m.from or '' }}</div><div class="snippet">{{ m.date or '' }} · Size: {{ m.size or '' }}</div></div>{% endfor %}
</div></div>
<div class="message-view">
{% if inbox.selected_message %}<div class="message-head"><h3>{{ inbox.selected_message.subject or '(No subject)' }}</h3><p><b>From:</b> {{ inbox.selected_message.from or '' }}</p><p><b>Date:</b> {{ inbox.selected_message.date or '' }}</p>{% if inbox.selected_message._otp %}<p>OTP:</p><p class="otp">{{ inbox.selected_message._otp }}</p><button onclick="copyText('{{ inbox.selected_message._otp }}')">Copy OTP</button>{% endif %}</div><h4>Nội dung mail mới nhất</h4><div class="body-box">{{ inbox.selected_message._body_text }}</div>{% else %}<h3>Chưa có mail</h3><p>Email này chưa nhận được mail nào.</p>{% endif %}
</div>
</div>
</div>
'''

def render_inbox_card(inbox):
    return render_template_string(INBOX_CARD, inbox=inbox)
app.jinja_env.globals.update(render_inbox_card=render_inbox_card)

def render(**kwargs):
    generated_emails = session.get('generated_emails')
    generated_inboxes = [build_inbox_data(i['email']) for i in generated_emails] if generated_emails else []
    defaults = dict(domains=load_domains(), generated_emails=generated_emails, generated_inboxes=generated_inboxes, generate_error=None, error=None, admin=session.get('admin', False), inbox_email=None, single_inbox=None)
    defaults.update(kwargs)
    return render_template_string(HTML, **defaults)

@app.route('/')
def home():
    return render()

@app.route('/inbox')
def inbox():
    email = request.args.get('email','').strip().lower()
    if not email or '@' not in email:
        return render(error='Email sai. Phải nhập đủ dạng name@domain.com', inbox_email=email)
    if not is_allowed_domain(email):
        return render(error='Domain này chưa được admin cho phép.', inbox_email=email)
    return render(inbox_email=email, single_inbox=build_inbox_data(email))

@app.route('/generate', methods=['POST'])
def generate():
    if not session.get('admin'):
        return redirect(url_for('home'))
    generated_emails, generate_error = generate_two_cross_domain()
    if generate_error:
        return render(generate_error=generate_error)
    session['generated_emails'] = generated_emails
    return redirect(url_for('home'))

@app.route('/admin-login', methods=['POST'])
def admin_login():
    if request.form.get('password','') == ADMIN_PASSWORD:
        session['admin'] = True
    return redirect(url_for('home'))

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('admin', None)
    return redirect(url_for('home'))

@app.route('/api/mailbox')
def api_mailbox():
    email = request.args.get('email','').strip().lower()
    if not email or '@' not in email:
        return jsonify({'ok': False, 'error': 'Email sai.'}), 400
    if not is_allowed_domain(email):
        return jsonify({'ok': False, 'error': 'Domain chưa được admin cho phép.'}), 403
    try:
        messages, count = get_mailbox(email)
        safe = [{'id':m.get('id',''), 'mailbox':m.get('mailbox',''), 'from':m.get('from',''), 'subject':m.get('subject',''), 'date':m.get('date',''), 'size':m.get('size','')} for m in messages]
        return jsonify({'ok': True, 'email': email, 'count': count, 'messages': safe})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/message')
def api_message():
    email = request.args.get('email','').strip().lower()
    msg_id = request.args.get('id','').strip()
    if not email or '@' not in email:
        return jsonify({'ok': False, 'error': 'Email sai.'}), 400
    if not msg_id:
        return jsonify({'ok': False, 'error': 'Thiếu message id.'}), 400
    if not is_allowed_domain(email):
        return jsonify({'ok': False, 'error': 'Domain chưa được admin cho phép.'}), 403
    try:
        msg = get_message(email, msg_id)
        return jsonify({'ok': True, 'message': {'id': msg.get('id', msg_id), 'from': msg.get('from',''), 'subject': msg.get('subject',''), 'date': msg.get('date',''), 'body': msg.get('_body_text',''), 'otp': msg.get('_otp')}})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
