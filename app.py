from flask import Flask, request, redirect, url_for, render_template_string, session
import requests
import re
import random
import os
import json

# =========================
# CONFIG
# =========================
APP_SECRET = os.environ.get("APP_SECRET", "change_this_secret")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
DOMAINS_FILE = "domains.json"

API_MAILBOX = "https://api.catchmail.io/api/v1/mailbox"
API_MESSAGE = "https://api.catchmail.io/api/v1/message/{}"

# 6 domain mặc định của bạn
DEFAULT_DOMAINS = [
    "thanhhoa.fun",
    "thanhhoa.store",
    "shop36.online",
    "shop36.site",
    "shopthanhhoa.online",
    "diccumay.online",
]

# Tên người Việt không dấu
HO = [
    "nguyen", "tran", "le", "pham", "hoang", "huynh", "phan",
    "vu", "vo", "dang", "bui", "do", "ho", "ngo", "duong", "ly"
]

TEN_DEM = [
    "van", "minh", "quang", "duc", "gia", "thanh", "tuan",
    "bao", "anh", "nhat", "hoai", "trung", "ngoc", "huu"
]

TEN = [
    "anh", "hieu", "huy", "long", "nam", "phuc", "khang",
    "dat", "son", "duy", "tuan", "phong", "linh", "trang",
    "vy", "ngan", "thao", "han", "nhi", "my"
]

app = Flask(__name__)
app.secret_key = APP_SECRET


# =========================
# DOMAIN FUNCTIONS
# =========================
def load_domains():
    """
    Load domain từ domains.json.
    Nếu chưa có domains.json thì tự tạo bằng 6 domain mặc định.
    """
    if not os.path.exists(DOMAINS_FILE):
        save_domains(DEFAULT_DOMAINS)

    with open(DOMAINS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_domains(domains):
    domains = sorted(list(set([d.strip().lower() for d in domains if d.strip()])))
    with open(DOMAINS_FILE, "w", encoding="utf-8") as f:
        json.dump(domains, f, indent=2, ensure_ascii=False)


def clean_domain(domain):
    domain = domain.strip().lower()
    domain = domain.replace("https://", "").replace("http://", "")
    domain = domain.replace("/", "")
    return domain


def email_domain(email):
    if "@" not in email:
        return ""
    return email.split("@")[-1].lower().strip()


def is_allowed_domain(email):
    return email_domain(email) in load_domains()


# =========================
# EMAIL FUNCTIONS
# =========================
def random_email(domain):
    name = f"{random.choice(HO)}{random.choice(TEN_DEM)}{random.choice(TEN)}{random.randint(1000, 9999)}"
    return f"{name}@{domain}"


def generate_all_domains():
    """
    Admin bấm tạo email:
    - Tạo 1 email cho mỗi domain trong danh sách
    - Nếu có 6 domain thì tạo 6 email
    - Không trùng domain vì mỗi domain chỉ tạo 1 email
    """
    domains = load_domains()

    if not domains:
        return None, "Chưa có domain nào trong danh sách."

    emails = []

    for domain in domains:
        emails.append({
            "domain": domain,
            "email": random_email(domain)
        })

    return emails, None


# =========================
# CATCHMAIL FUNCTIONS
# =========================
def get_body(msg):
    body_data = msg.get("body", "")

    if isinstance(body_data, dict):
        return body_data.get("text", "") or body_data.get("html", "") or str(body_data)

    return str(body_data)


def find_otp(text):
    # Ưu tiên OTP 6 số
    match6 = re.findall(r"\b\d{6}\b", text)
    if match6:
        return match6[0]

    # Fallback: 4-8 số
    match = re.findall(r"\b\d{4,8}\b", text)
    if match:
        return match[0]

    return None


def get_mailbox(email):
    res = requests.get(
        API_MAILBOX,
        params={"address": email},
        timeout=10
    )

    data = res.json()
    return data.get("messages", []), data.get("count", 0)


def get_message(email, msg_id):
    msg = requests.get(
        API_MESSAGE.format(msg_id),
        params={"mailbox": email},
        timeout=10
    ).json()

    body = get_body(msg)
    msg["_body_text"] = body
    msg["_otp"] = find_otp(body)

    return msg


def build_inbox_data(email):
    try:
        messages, count = get_mailbox(email)

        selected_message = None
        selected_id = None

        if messages:
            selected_id = messages[0].get("id")
            selected_message = get_message(email, selected_id)

        return {
            "email": email,
            "messages": messages,
            "count": count,
            "selected_id": selected_id,
            "selected_message": selected_message,
            "error": None
        }

    except Exception as e:
        return {
            "email": email,
            "messages": [],
            "count": 0,
            "selected_id": None,
            "selected_message": None,
            "error": str(e)
        }


# =========================
# HTML
# =========================
HTML = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>CatchMail Inbox Tool</title>
    <style>
        * { box-sizing: border-box; }

        body {
            font-family: Arial, sans-serif;
            max-width: 1180px;
            margin: 24px auto;
            padding: 0 16px;
            background: #fafafa;
            color: #111;
        }

        input, select, button {
            padding: 10px;
            font-size: 15px;
        }

        button {
            cursor: pointer;
            border: 1px solid #bbb;
            background: white;
            border-radius: 5px;
        }

        button:hover {
            background: #f2f2f2;
        }

        .box {
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 16px;
            margin: 16px 0;
            background: white;
        }

        .admin-only {
            border-color: #c6a700;
            background: #fffdf0;
        }

        .error {
            color: #b00020;
            font-weight: bold;
        }

        .ok {
            color: green;
            font-weight: bold;
        }

        .small {
            color: #666;
            font-size: 13px;
        }

        .otp {
            font-size: 26px;
            font-weight: bold;
            color: #d00;
        }

        .input-row {
            display: flex;
            gap: 8px;
        }

        .input-row input {
            flex: 1;
        }

        .generated-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }

        .generated-table th,
        .generated-table td {
            border: 1px solid #ddd;
            padding: 10px;
        }

        .generated-table th {
            background: #f1f1f1;
        }

        .generated-email {
            font-weight: bold;
        }

        .notice {
            border: 1px solid #d8d8d8;
            background: white;
            padding: 14px;
            border-radius: 10px;
            margin: 14px 0;
        }

        .inline-inbox-section {
            margin-top: 18px;
        }

        .inbox-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            align-items: start;
        }

        .mailbox-card {
            border: 1px solid #d8d8d8;
            border-radius: 10px;
            background: #fff;
            overflow: hidden;
        }

        .mailbox-top {
            text-align: center;
            padding: 16px;
            border-bottom: 1px solid #ddd;
            background: #fbfbfb;
        }

        .email-line {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 0;
            margin: 8px 0;
        }

        .email-box {
            border: 1px solid #ccc;
            padding: 10px;
            min-width: 300px;
            font-weight: bold;
            background: white;
            overflow-wrap: anywhere;
        }

        .refresh-line {
            display: flex;
            justify-content: center;
            gap: 10px;
            align-items: center;
            margin-top: 8px;
        }

        .inbox-wrap {
            display: grid;
            grid-template-columns: 38% 62%;
            min-height: 330px;
        }

        .inbox-list {
            border-right: 1px solid #ddd;
            max-height: 420px;
            overflow-y: auto;
        }

        .inbox-title {
            padding: 10px;
            border-bottom: 1px solid #ddd;
            font-size: 18px;
            background: #fff;
            position: sticky;
            top: 0;
        }

        .message-item {
            display: block;
            padding: 10px;
            border-bottom: 1px solid #eee;
            color: #111;
            text-decoration: none;
        }

        .message-item:hover {
            background: #f5f5f5;
        }

        .message-item.active {
            background: #eef5ff;
        }

        .subject {
            font-weight: bold;
            font-size: 15px;
            margin-bottom: 4px;
        }

        .from {
            color: #0066cc;
            font-size: 13px;
            margin-bottom: 4px;
            overflow-wrap: anywhere;
        }

        .snippet {
            color: #555;
            font-size: 12px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .message-view {
            padding: 12px;
            max-height: 420px;
            overflow-y: auto;
        }

        .message-head {
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
            margin-bottom: 10px;
        }

        .message-head h3 {
            margin-top: 0;
        }

        .body-box {
            border: 1px solid #ddd;
            padding: 10px;
            min-height: 150px;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            background: #fff;
            font-size: 13px;
        }

        @media (max-width: 980px) {
            .inbox-grid {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 700px) {
            .input-row {
                flex-direction: column;
            }

            .inbox-wrap {
                grid-template-columns: 1fr;
            }

            .inbox-list {
                border-right: 0;
                border-bottom: 1px solid #ddd;
            }
        }
    </style>
</head>
<body>
    <h2>🚀 CatchMail Inbox Tool</h2>

    <div class="box">
        <h3>🔍 Người dùng: nhập full email để xem inbox / OTP</h3>

        <form method="GET" action="/inbox" class="input-row">
            <input
                type="text"
                name="email"
                placeholder="Ví dụ: nguyenvananh1234@thanhhoa.store"
                value="{{ inbox_email or '' }}"
                required
            >
            <button type="submit">Mở inbox</button>
        </form>

        {% if error %}
            <p class="error">{{ error }}</p>
        {% endif %}
    </div>

    {% if inbox_email and not error %}
        {{ render_inbox_card(single_inbox)|safe }}
    {% endif %}

    <div class="box admin-only">
        <h3>🔐 Admin</h3>

        {% if admin %}
            <p class="ok">Đang đăng nhập admin.</p>

            <h4>🎲 Tạo email random bằng tất cả domain</h4>
            <p class="small">
                Chỉ admin mới dùng được.
                Mỗi lần tạo sẽ tạo 1 email cho mỗi domain trong danh sách.
            </p>

            <form method="POST" action="/generate">
                <button type="submit">Tạo email bằng tất cả domain</button>
            </form>

            {% if generate_error %}
                <p class="error">{{ generate_error }}</p>
            {% endif %}

            {% if generated_emails %}
                <div class="notice">
                    <h4>✅ Bảng thông báo email vừa tạo</h4>

                    <table class="generated-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Domain</th>
                                <th>Email</th>
                                <th>Copy</th>
                            </tr>
                        </thead>

                        <tbody>
                            {% for item in generated_emails %}
                            <tr>
                                <td>{{ loop.index }}</td>
                                <td>{{ item.domain }}</td>
                                <td class="generated-email">{{ item.email }}</td>
                                <td>
                                    <button onclick="navigator.clipboard.writeText('{{ item.email }}')">
                                        Copy
                                    </button>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>

                    <div class="inline-inbox-section">
                        <h4>📬 Inbox tự hiện cho tất cả email vừa tạo</h4>

                        <div class="inbox-grid">
                            {% for inbox in generated_inboxes %}
                                {{ render_inbox_card(inbox)|safe }}
                            {% endfor %}
                        </div>
                    </div>
                </div>
            {% endif %}

            <hr>

            <h4>➕ Thêm domain</h4>

            <form method="POST" action="/add-domain" class="input-row">
                <input type="text" name="domain" placeholder="domainmoi.com">
                <button type="submit">Thêm domain</button>
            </form>

            <p>Domain hiện có:</p>
            <table class="generated-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Domain</th>
                        <th>Xóa</th>
                    </tr>
                </thead>
                <tbody>
                    {% for d in domains %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td><b>{{ d }}</b></td>
                        <td>
                            <form method="POST" action="/delete-domain" onsubmit="return confirm('Xóa domain {{ d }} khỏi danh sách?');">
                                <input type="hidden" name="domain" value="{{ d }}">
                                <button type="submit">Xóa</button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>

            <form method="POST" action="/logout">
                <button type="submit">Đăng xuất admin</button>
            </form>

        {% else %}
            <p class="small">Chỉ admin mới tạo email random và thêm domain.</p>

            <form method="POST" action="/admin-login" class="input-row">
                <input type="password" name="password" placeholder="Mật khẩu admin">
                <button type="submit">Đăng nhập admin</button>
            </form>
        {% endif %}
    </div>

    <p class="small">
        Tool chỉ đọc được email thuộc domain đã trỏ MX về CatchMail.
        Không thể đọc Gmail cá nhân nếu không có OAuth/quyền Gmail.
    </p>
</body>
</html>
"""

INBOX_CARD = """
<div class="mailbox-card">
    <div class="mailbox-top">
        <div class="small">Your temporary email address</div>

        <div class="email-line">
            <div class="email-box">{{ inbox.email }}</div>
            <button onclick="navigator.clipboard.writeText('{{ inbox.email }}')">
                📋 Copy
            </button>
        </div>

        <div class="refresh-line">
            <a href="{{ url_for('inbox', email=inbox.email) }}">
                <button>⟳ Refresh riêng</button>
            </a>
        </div>

        {% if inbox.error %}
            <p class="error">Lỗi: {{ inbox.error }}</p>
        {% endif %}
    </div>

    <div class="inbox-wrap">
        <div class="inbox-list">
            <div class="inbox-title">
                Inbox <span class="small">({{ inbox.count }})</span>
            </div>

            {% if not inbox.messages %}
                <div style="padding: 14px;">❌ Chưa có mail nào.</div>
            {% endif %}

            {% for m in inbox.messages %}
                <div class="message-item {% if inbox.selected_id == m.id %}active{% endif %}">
                    <div class="subject">{{ m.subject or '(No subject)' }}</div>
                    <div class="from">{{ m.from or '' }}</div>
                    <div class="snippet">{{ m.date or '' }} · Size: {{ m.size or '' }}</div>
                </div>
            {% endfor %}
        </div>

        <div class="message-view">
            {% if inbox.selected_message %}
                <div class="message-head">
                    <h3>{{ inbox.selected_message.subject or '(No subject)' }}</h3>
                    <p><b>From:</b> {{ inbox.selected_message.from or '' }}</p>
                    <p><b>Date:</b> {{ inbox.selected_message.date or '' }}</p>

                    {% if inbox.selected_message._otp %}
                        <p>OTP:</p>
                        <p class="otp">{{ inbox.selected_message._otp }}</p>
                        <button onclick="navigator.clipboard.writeText('{{ inbox.selected_message._otp }}')">
                            Copy OTP
                        </button>
                    {% endif %}
                </div>

                <h4>Nội dung mail mới nhất</h4>
                <div class="body-box">{{ inbox.selected_message._body_text }}</div>
            {% else %}
                <h3>Chưa có mail</h3>
                <p>Email này chưa nhận được mail nào.</p>
            {% endif %}
        </div>
    </div>
</div>
"""


def render_inbox_card(inbox):
    return render_template_string(INBOX_CARD, inbox=inbox)


app.jinja_env.globals.update(render_inbox_card=render_inbox_card)


# =========================
# RENDER HELPER
# =========================
def render(**kwargs):
    generated_emails = session.get("generated_emails")
    generated_inboxes = []

    if generated_emails:
        generated_inboxes = [
            build_inbox_data(item["email"])
            for item in generated_emails
        ]

    defaults = dict(
        domains=load_domains(),
        generated_emails=generated_emails,
        generated_inboxes=generated_inboxes,
        generate_error=None,
        error=None,
        admin=session.get("admin", False),
        inbox_email=None,
        single_inbox=None
    )

    defaults.update(kwargs)

    return render_template_string(HTML, **defaults)


# =========================
# ROUTES
# =========================
@app.route("/", methods=["GET"])
def home():
    return render()


@app.route("/inbox", methods=["GET"])
def inbox():
    email = request.args.get("email", "").strip().lower()

    if not email or "@" not in email:
        return render(
            error="Email sai. Phải nhập đủ dạng name@domain.com",
            inbox_email=email
        )

    if not is_allowed_domain(email):
        return render(
            error="Domain này chưa được admin cho phép.",
            inbox_email=email
        )

    return render(
        inbox_email=email,
        single_inbox=build_inbox_data(email)
    )


@app.route("/generate", methods=["POST"])
def generate():
    if not session.get("admin"):
        return redirect(url_for("home"))

    generated_emails, generate_error = generate_all_domains()

    if generate_error:
        return render(generate_error=generate_error)

    session["generated_emails"] = generated_emails

    return redirect(url_for("home"))


@app.route("/admin-login", methods=["POST"])
def admin_login():
    if request.form.get("password", "") == ADMIN_PASSWORD:
        session["admin"] = True

    return redirect(url_for("home"))


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("admin", None)

    return redirect(url_for("home"))


@app.route("/add-domain", methods=["POST"])
def add_domain():
    if not session.get("admin"):
        return redirect(url_for("home"))

    domain = clean_domain(request.form.get("domain", ""))

    if domain:
        domains = load_domains()
        domains.append(domain)
        save_domains(domains)

    return redirect(url_for("home"))


@app.route("/delete-domain", methods=["POST"])
def delete_domain():
    if not session.get("admin"):
        return redirect(url_for("home"))

    domain = clean_domain(request.form.get("domain", ""))

    if domain:
        domains = load_domains()
        domains = [d for d in domains if d != domain]
        save_domains(domains)

        # Nếu domain bị xóa đang nằm trong email vừa tạo thì bỏ bảng cũ để tránh lỗi
        session.pop("generated_emails", None)

    return redirect(url_for("home"))

# =========================
# LOCAL RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
