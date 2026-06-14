from flask import Flask, request, jsonify, render_template_string, redirect, session, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import hashlib
import telebot
import json

app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database_new.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = None

# -------------------- مدل‌ها --------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    price = db.Column(db.Integer)
    is_free = db.Column(db.Boolean, default=False)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, default=1)
    product = db.relationship('Product')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_price = db.Column(db.Integer)
    status = db.Column(db.String(20), default='pending')
    codes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

# -------------------- تلگرام (اختیاری) --------------------
TELEGRAM_BOT_TOKEN = 'fake:token'
TELEGRAM_CHAT_ID = '123'
if ':' in TELEGRAM_BOT_TOKEN and len(TELEGRAM_BOT_TOKEN) > 10:
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
else:
    bot = None

ADMIN_PANEL_EXTRA_PASSWORD = 'mincraft2484'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------- صفحه اصلی فروشگاه (بدون «مشاهده همه») --------------------
@app.route('/')
def home():
    skins = Product.query.filter_by(category='skin').limit(6).all()
    maps = Product.query.filter_by(category='map').limit(6).all()
    heads = Product.query.filter_by(category='head').limit(6).all()
    free_items = Product.query.filter_by(is_free=True).all()
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>پیکلمینه | بهترین محتوای ماینکرفت</title>
        <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/font-face.css" rel="stylesheet">
        <style>
            * { margin:0; padding:0; box-sizing:border-box; }
            body { font-family: 'Vazir', Tahoma, sans-serif; background: #0a0a0a; color: #eee; line-height: 1.6; }
            a { text-decoration: none; color: #2ecc71; }
            button, input, select, textarea { font-family: 'Vazir', Tahoma, sans-serif; }
            .container { max-width: 1200px; margin: auto; padding: 0 20px; }
            header { background: #000000; padding: 20px 0; border-bottom: 3px solid #2ecc71; }
            .logo h1 { font-size: 2rem; color: #2ecc71; }
            .logo p { color: #aaa; }
            nav { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 15px; }
            nav a { background: #1a1a1a; padding: 8px 15px; border-radius: 25px; transition: 0.3s; color: #eee; }
            nav a:hover, nav a.active { background: #2ecc71; color: #000; }
            .hero { background: linear-gradient(135deg, #1a3a1a, #000000); padding: 50px 0; text-align: center; border-radius: 30px; margin: 30px 0; border: 1px solid #2ecc71; }
            .hero h2 { font-size: 2.5rem; }
            .btn { display: inline-block; background: #2ecc71; color: #000; padding: 12px 25px; border-radius: 30px; margin-top: 15px; font-weight: bold; }
            .section { margin: 50px 0; }
            .section-title { font-size: 1.8rem; border-right: 5px solid #2ecc71; padding-right: 15px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
            .product-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 25px; }
            .product-card { background: #111; border-radius: 20px; padding: 15px; text-align: center; transition: 0.3s; border: 1px solid #2ecc71; }
            .product-card:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(46,204,113,0.2); }
            .price { color: #2ecc71; font-size: 1.3rem; margin: 10px 0; }
            .free { color: #4caf50; }
            button.add-to-cart { background: #2ecc71; border: none; padding: 8px 15px; border-radius: 20px; cursor: pointer; font-weight: bold; color: #000; }
            footer { background: #000; padding: 40px 0; margin-top: 50px; border-top: 2px solid #2ecc71; }
            .footer-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 30px; }
            .newsletter input { padding: 10px; border-radius: 25px; border: none; width: 70%; margin-left: 5px; background: #222; color: #fff; }
            .newsletter button { background: #2ecc71; border: none; padding: 10px 20px; border-radius: 25px; cursor: pointer; font-weight: bold; }
            .cart-icon { position: fixed; bottom: 20px; left: 20px; background: #2ecc71; color: #000; width: 55px; height: 55px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; cursor: pointer; z-index: 1000; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
            .cart-sidebar { position: fixed; top: 0; left: -350px; width: 350px; height: 100%; background: #0a0a0a; z-index: 1001; padding: 20px; transition: 0.4s; box-shadow: 0 0 15px rgba(0,0,0,0.5); overflow-y: auto; border-left: 3px solid #2ecc71; }
            .cart-sidebar.open { left: 0; }
            .close-cart { float: left; font-size: 28px; cursor: pointer; color: #2ecc71; }
            .modal { display: none; position: fixed; z-index: 2000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.8); justify-content: center; align-items: center; }
            .modal-content { background: #111; border-radius: 30px; padding: 30px; max-width: 500px; width: 90%; text-align: center; border: 2px solid #2ecc71; direction: rtl; }
            .modal-content h2 { color: #2ecc71; margin-bottom: 20px; }
            .code-list { background: #1a1a1a; padding: 15px; border-radius: 20px; margin: 15px 0; text-align: right; }
            .code-item { font-family: monospace; font-size: 1.1rem; margin: 5px 0; }
            .bank-info { background: #0a0a0a; padding: 15px; border-radius: 15px; margin: 10px 0; font-weight: bold; }
            .close-modal { background: #2ecc71; border: none; padding: 10px 20px; border-radius: 25px; cursor: pointer; font-weight: bold; margin-top: 10px; }
            .view-all-link { background: #2ecc71; color: #000; padding: 5px 15px; border-radius: 20px; font-size: 0.9rem; font-weight: bold; }
            @media (max-width: 768px) { .product-grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); } }
        </style>
    </head>
    <body>
        <header>
            <div class="container">
                <div class="logo"><h1>پیکلمینه</h1><p>بهترین محتوای ماینکرفت</p></div>
                <nav>
                    <a href="/" class="active">خانه</a>
                    <a href="/products/skin">اسکین‌ها</a>
                    <a href="/products/map">مپ‌ها</a>
                    <a href="/products/head">هدها</a>
                    <a href="/news">اخبار</a>
                    <a href="#" id="loginBtn">ورود / ثبت نام</a>
                    {% if current_user.is_authenticated and current_user.is_admin %}<a href="/admin_panel">پنل ادمین</a>{% endif %}
                </nav>
            </div>
        </header>
        <div class="container">
            <div class="hero"><h2>اسکین، هد، مپ و پک‌های اختصاصی</h2><p>برای یک تجربه‌ی متفاوت!</p><a href="/products/all" class="btn">مشاهده محصولات</a></div>
            
            <!-- اسکین‌ها -->
            <div class="section">
                <div class="section-title">
                    <span>🔥 جدیدترین اسکین‌ها</span>
                    <a href="/products/skin" class="view-all-link">مشاهده همه</a>
                </div>
                <div class="product-grid">{% for s in skins %}<div class="product-card" data-id="{{ s.id }}"><h3>{{ s.name }}</h3><div class="price">{{ s.price }} تومان</div><button class="add-to-cart" data-id="{{ s.id }}">➕ افزودن به سبد</button></div>{% endfor %}</div>
            </div>
            
            <!-- مپ‌ها -->
            <div class="section">
                <div class="section-title">
                    <span>🗺️ مپ‌های محبوب</span>
                    <a href="/products/map" class="view-all-link">مشاهده همه</a>
                </div>
                <div class="product-grid">{% for m in maps %}<div class="product-card" data-id="{{ m.id }}"><h3>{{ m.name }}</h3><div class="price">{{ m.price }} تومان</div><button class="add-to-cart" data-id="{{ m.id }}">➕ افزودن به سبد</button></div>{% endfor %}</div>
            </div>
            
            <!-- محتوای رایگان (بدون دکمه مشاهده همه) -->
            <div class="section">
                <div class="section-title"><span>🎁 محتوای رایگان</span></div>
                <div class="product-grid">{% for f in free_items %}<div class="product-card"><h3>{{ f.name }}</h3><div class="price free">رایگان</div><button class="add-to-cart" data-id="{{ f.id }}">دانلود کنید</button></div>{% endfor %}</div>
            </div>
            
            <!-- اخبار (به زودی) -->
            <div class="section">
                <div class="section-title">
                    <span>📰 آخرین اخبار ماینکرفت</span>
                    <a href="/news" class="view-all-link">مشاهده همه</a>
                </div>
                <div style="background:#111; border:1px solid #2ecc71; border-radius:20px; padding:30px; text-align:center; margin-top:20px;">
                    <div style="font-size:40px; margin-bottom:15px;">📰</div>
                    <h3 style="color:#2ecc71; margin-bottom:10px;">به زودی...</h3>
                    <p style="color:#ccc;">اخبار جدید، راهنماها و رویدادهای ویژه به زودی در این بخش قرار می‌گیرند.</p>
                </div>
            </div>
        </div>
        <footer>
            <div class="container">
                <div class="footer-grid">
                    <div><h4>درباره ما</h4><p>PixelMine مرجع تخصصی محتوای ماینکرفت</p></div>
                    <div><h4>ارتباط با ما</h4><p>📞 09133377688</p><p>📱 تلگرام: <a href="https://t.me/mr_javaheriam" target="_blank">@mr_javaheriam</a></p></div>
                    <div><h4>دسترسی سریع</h4><p><a href="/">خانه</a> | <a href="/products/all">محصولات</a> | <a href="/news">اخبار</a></p></div>
                    <div class="newsletter"><h4>خبرنامه</h4><input type="email" placeholder="ایمیل"><button>عضویت</button></div>
                </div>
            </div>
        </footer>
        <div class="cart-icon" id="cartIcon">🛒</div>
        <div class="cart-sidebar" id="cartSidebar"><span class="close-cart" id="closeCart">&times;</span><h2>سبد خرید</h2><div id="cartItems"></div><hr><div>جمع: <span id="cartTotal">0</span> تومان</div><button id="checkoutBtn" class="btn">تسویه حساب</button></div>
        <div id="paymentModal" class="modal"><div class="modal-content"><h2>💳 اطلاعات پرداخت</h2><div id="modalCodes"></div><div class="bank-info"><p>🏦 شماره کارت: <strong>632145586995</strong></p><p>💰 مبلغ کل: <span id="modalTotal"></span> تومان</p></div><p>✅ پس از واریز، تصویر رسید را در یکی از پیام‌رسان‌های زیر ارسال کنید:</p><p>📱 تلگرام: <a href="https://t.me/mr_javaheriam" target="_blank">@mr_javaheriam</a><br>📱 بله | 📱 ایتا (با همین آیدی)</p><button class="close-modal" onclick="closeModal()">بستن</button></div></div>
        <script>
            const sidebar = document.getElementById('cartSidebar'), icon = document.getElementById('cartIcon'), close = document.getElementById('closeCart');
            icon.onclick = () => { sidebar.classList.add('open'); loadCart(); };
            close.onclick = () => sidebar.classList.remove('open');
            async function loadCart() { let res = await fetch('/api/cart'); if(res.status===401){ alert('لطفا وارد شوید'); return; } let items = await res.json(); let html='', total=0; items.forEach(i=>{ total+=i.total; html+=`<div>${i.product.name} × ${i.quantity} = ${i.total} تومان <button onclick="removeItem(${i.id})">حذف</button></div>`; }); document.getElementById('cartItems').innerHTML = html||'سبد خالی'; document.getElementById('cartTotal').innerText = total; }
            window.removeItem = async (id) => { await fetch(`/api/cart/remove/${id}`, {method:'DELETE'}); loadCart(); };
            document.querySelectorAll('.add-to-cart').forEach(btn=>{ btn.onclick = async (e) => { let id = btn.getAttribute('data-id'); let res = await fetch('/api/cart/add', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id:id})}); if(res.status===401) alert('ابتدا وارد شوید'); else alert('اضافه شد'); }; });
            document.getElementById('checkoutBtn').onclick = async () => { let res = await fetch('/api/checkout', {method:'POST'}); let data = await res.json(); if(res.ok) { let codesHtml = '<div class=\"code-list\"><strong>🎫 کدهای اختصاصی:</strong><br>'; data.codes.forEach(c => { codesHtml += `<div class=\"code-item\">📦 ${c.product} : <span style=\"color:#2ecc71;\">${c.code}</span></div>`; }); codesHtml += '</div>'; document.getElementById('modalCodes').innerHTML = codesHtml; document.getElementById('modalTotal').innerText = data.total; document.getElementById('paymentModal').style.display = 'flex'; loadCart(); sidebar.classList.remove('open'); } else { alert('خطا: ' + (data.error || 'مشخص نیست')); } };
            function closeModal() { document.getElementById('paymentModal').style.display = 'none'; }
            window.onclick = function(event) { let modal = document.getElementById('paymentModal'); if (event.target == modal) modal.style.display = 'none'; }
            document.getElementById('loginBtn').onclick = async () => { let action = prompt('ورود (1) یا ثبت نام (2)؟'); if(action==='1'){ let u=prompt('نام کاربری'), p=prompt('رمز'); let r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})}); let d=await r.json(); alert(d.message||d.error); if(r.ok) location.reload(); } else if(action==='2'){ let u=prompt('نام کاربری'), e=prompt('ایمیل'), p=prompt('رمز'); let r=await fetch('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,email:e,password:p})}); let d=await r.json(); alert(d.message||d.error); } };
        </script>
    </body>
    </html>
    ''', skins=skins, maps=maps, heads=heads, free_items=free_items)

# -------------------- صفحات محصولات (فونت یکسان) --------------------
@app.route('/products/<category>')
def products_list(category):
    if category == 'all':
        products = Product.query.all()
    else:
        products = Product.query.filter_by(category=category).all()
    category_name = {'skin':'اسکین', 'map':'مپ', 'head':'هد', 'all':'همه محصولات'}.get(category, 'محصولات')
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head><meta charset="UTF-8"><title>لیست {{category_name}} | پیکلمینه</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/font-face.css" rel="stylesheet">
    <style>
        body { font-family: 'Vazir', Tahoma, sans-serif; background: #0a0a0a; color: #eee; margin:0; padding:20px; direction:rtl; }
        button, input { font-family: 'Vazir', Tahoma, sans-serif; }
        .container { max-width:1200px; margin:auto; }
        .product-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:20px; }
        .product-card { background:#111; border-radius:20px; padding:15px; text-align:center; border:1px solid #2ecc71; }
        .price { color:#2ecc71; }
        button { background:#2ecc71; border:none; padding:8px 15px; border-radius:20px; cursor:pointer; font-weight:bold; }
        .back { display:inline-block; margin-bottom:20px; background:#2ecc71; color:#000; padding:8px 20px; border-radius:30px; text-decoration:none; }
        a { color:#2ecc71; text-decoration:none; }
    </style></head>
    <body><div class="container"><a href="/" class="back">← بازگشت به خانه</a><h1>{{category_name}}</h1><div class="product-grid">{% for p in products %}<div class="product-card"><h3>{{p.name}}</h3><div class="price">{{p.price}} تومان</div><button class="add-to-cart" data-id="{{p.id}}">➕ سبد</button></div>{% endfor %}</div></div>
    <script>
        document.querySelectorAll('.add-to-cart').forEach(btn=>{ btn.onclick = async (e) => { let id = btn.getAttribute('data-id'); let res = await fetch('/api/cart/add', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id:id})}); if(res.status===401) alert('ابتدا وارد شوید'); else alert('اضافه شد'); }; });
    </script></body></html>
    ''', products=products, category_name=category_name)

@app.route('/news')
def news():
    return '''
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>اخبار | پیکلمینه</title>
        <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/font-face.css" rel="stylesheet">
        <style>
            * { margin:0; padding:0; box-sizing:border-box; }
            body {
                font-family: 'Vazir', Tahoma, sans-serif;
                background: #0a0a0a;
                color: #eee;
                line-height: 1.6;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }
            a { text-decoration: none; color: #2ecc71; }
            .container { max-width: 1200px; margin: auto; padding: 0 20px; }
            header { background: #000000; padding: 20px 0; border-bottom: 3px solid #2ecc71; }
            .logo h1 { font-size: 2rem; color: #2ecc71; }
            .logo p { color: #aaa; }
            nav { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 15px; }
            nav a { background: #1a1a1a; padding: 8px 15px; border-radius: 25px; transition: 0.3s; color: #eee; }
            nav a:hover, nav a.active { background: #2ecc71; color: #000; }
            footer { background: #000; padding: 40px 0; margin-top: auto; border-top: 2px solid #2ecc71; }
            .footer-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 30px; }
            .newsletter input { padding: 10px; border-radius: 25px; border: none; width: 70%; margin-left: 5px; background: #222; color: #fff; }
            .newsletter button { background: #2ecc71; border: none; padding: 10px 20px; border-radius: 25px; cursor: pointer; font-weight: bold; }
            .coming-soon {
                background: #111;
                border-radius: 30px;
                padding: 60px 30px;
                text-align: center;
                margin: 60px auto;
                max-width: 700px;
                border: 1px solid #2ecc71;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            }
            .coming-soon h2 {
                color: #2ecc71;
                font-size: 2.5rem;
                margin-bottom: 20px;
            }
            .coming-soon p {
                color: #ccc;
                font-size: 1.2rem;
                margin-bottom: 30px;
            }
            .icon {
                font-size: 70px;
                margin-bottom: 20px;
            }
            .btn-home {
                display: inline-block;
                background: #2ecc71;
                color: #000;
                padding: 12px 30px;
                border-radius: 40px;
                font-weight: bold;
                transition: 0.2s;
            }
            .btn-home:hover {
                transform: scale(1.05);
                background: #27ae60;
                box-shadow: 0 5px 15px rgba(46,204,113,0.3);
            }
            @media (max-width: 768px) {
                .coming-soon { padding: 40px 20px; margin: 40px 20px; }
                .coming-soon h2 { font-size: 1.8rem; }
            }
        </style>
    </head>
    <body>
        <header>
            <div class="container">
                <div class="logo"><h1>پیکلمینه</h1><p>بهترین محتوای ماینکرفت</p></div>
                <nav>
                    <a href="/">خانه</a>
                    <a href="/products/skin">اسکین‌ها</a>
                    <a href="/products/map">مپ‌ها</a>
                    <a href="/products/head">هدها</a>
                    <a href="/news" class="active">اخبار</a>
                </nav>
            </div>
        </header>
        <div class="container">
            <div class="coming-soon">
                <div class="icon">📰</div>
                <h2>بخش اخبار در حال آماده‌سازی</h2>
                <p>به زودی اخبار جدید ماینکرفت، راهنماها و رویدادهای ویژه در این بخش منتشر خواهند شد.</p>
                <a href="/" class="btn-home">← بازگشت به صفحه اصلی</a>
            </div>
        </div>
        <footer>
            <div class="container">
                <div class="footer-grid">
                    <div><h4>درباره ما</h4><p>PixelMine مرجع تخصصی محتوای ماینکرفت</p></div>
                    <div><h4>ارتباط با ما</h4><p>📞 09133377688</p><p>📱 تلگرام: <a href="https://t.me/mr_javaheriam" target="_blank">@mr_javaheriam</a></p></div>
                    <div><h4>دسترسی سریع</h4><p><a href="/">خانه</a> | <a href="/products/all">محصولات</a> | <a href="/news">اخبار</a></p></div>
                    <div class="newsletter"><h4>خبرنامه</h4><input type="email" placeholder="ایمیل"><button>عضویت</button></div>
                </div>
            </div>
        </footer>
    </body>
    </html>
    '''

# -------------------- API ها --------------------
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'نام کاربری تکراری'}), 400
    hashed = hashlib.md5(data['password'].encode()).hexdigest()
    u = User(username=data['username'], email=data['email'], password=hashed, is_admin=False)
    db.session.add(u)
    db.session.commit()
    return jsonify({'message': 'ثبت نام موفق'})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and user.password == hashlib.md5(data['password'].encode()).hexdigest():
        login_user(user)
        return jsonify({'message': 'ورود موفق', 'is_admin': user.is_admin})
    return jsonify({'error': 'نام کاربری یا رمز اشتباه'}), 401

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'خارج شدید'})

@app.route('/api/cart/add', methods=['POST'])
@login_required
def add_cart():
    data = request.json
    prod = Product.query.get(data['product_id'])
    if not prod:
        return jsonify({'error': 'محصول یافت نشد'}), 404
    item = CartItem.query.filter_by(user_id=current_user.id, product_id=prod.id).first()
    if item:
        item.quantity += 1
    else:
        item = CartItem(user_id=current_user.id, product_id=prod.id)
        db.session.add(item)
    db.session.commit()
    return jsonify({'message': 'افزوده شد'})

@app.route('/api/cart', methods=['GET'])
@login_required
def get_cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    return jsonify([{'id':i.id, 'product':{'name':i.product.name,'price':i.product.price}, 'quantity':i.quantity, 'total':i.quantity*i.product.price} for i in items])

@app.route('/api/cart/remove/<int:item_id>', methods=['DELETE'])
@login_required
def remove_cart(item_id):
    item = CartItem.query.get(item_id)
    if item and item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return jsonify({'message': 'حذف شد'})

@app.route('/api/checkout', methods=['POST'])
@login_required
def checkout():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        return jsonify({'error': 'سبد خالی'}), 400
    total = sum(i.quantity * i.product.price for i in items)
    codes = []
    for item in items:
        for _ in range(item.quantity):
            if item.product.category == 'skin':
                prefix = 'A'
            elif item.product.category == 'map':
                prefix = 'B'
            elif item.product.category == 'head':
                prefix = 'C'
            else:
                prefix = 'F'
            code = f"{prefix}{item.product.id}"
            codes.append({'product': item.product.name, 'code': code})
    order = Order(user_id=current_user.id, total_price=total, codes=json.dumps(codes))
    db.session.add(order)
    db.session.commit()
    if bot:
        try:
            msg = f"سفارش #{order.id}\nکاربر: {current_user.username}\nمبلغ: {total} تومان\nکدها:\n" + "\n".join([f"{c['product']}: {c['code']}" for c in codes])
            bot.send_message(TELEGRAM_CHAT_ID, msg)
        except:
            pass
    for i in items:
        db.session.delete(i)
    db.session.commit()
    return jsonify({'message': 'success', 'codes': codes, 'total': total})

# -------------------- پنل ادمین با رمز دوم و جدول‌های مرتب --------------------
@app.route('/admin_panel', methods=['GET', 'POST'])
@login_required
def admin_panel():
    if not current_user.is_admin:
        return "دسترسی غیرمجاز: شما ادمین نیستید.", 403

    if session.get('admin_panel_verified'):
        products = Product.query.all()
        orders = Order.query.all()
        users = User.query.all()
        return render_template_string('''
        <!DOCTYPE html>
        <html dir="rtl">
        <head><meta charset="UTF-8"><title>پنل مدیریت</title>
        <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/font-face.css" rel="stylesheet">
        <style>
            body{font-family:'Vazir',Tahoma,sans-serif;background:#0a0a0a;color:#eee;padding:20px;}
            button, input, select { font-family: 'Vazir', Tahoma, sans-serif; }
            .card{background:#111;border-radius:20px;padding:20px;margin-bottom:20px;border:1px solid #2ecc71; overflow-x:auto;}
            input,select,button{padding:8px;margin:5px;border-radius:10px;border:none;}
            button{background:#2ecc71;cursor:pointer;font-weight:bold;}
            table{width:100%;border-collapse:collapse; word-break:break-word; white-space:normal;}
            th,td{padding:12px;border-bottom:1px solid #2ecc71; text-align:right; vertical-align:top;}
            th{background:#1a1a1a; color:#2ecc71;}
            .delete{background:#e74c3c;color:white;}
            .edit{background:#f39c12;color:black;}
            a{color:#2ecc71;text-decoration:none;}
            .security-buttons a{display:inline-block; margin:5px; padding:8px 15px; border-radius:20px; text-decoration:none; font-weight:bold;}
        </style></head>
        <body>
        <div class="card"><h2>➕ افزودن محصول جدید</h2>
        <form method="POST" action="/admin_add_product"><input name="name" placeholder="نام محصول" required><select name="category"><option value="skin">اسکین</option><option value="map">مپ</option><option value="head">هد</option></select><input name="price" type="number" placeholder="قیمت"><label><input type="checkbox" name="is_free"> رایگان</label><button type="submit">ذخیره</button></form></div>
        
        <div class="card"><h2>📦 مدیریت محصولات</h2>
        <div style="overflow-x:auto;">
        <table>
            <thead><tr><th>شناسه</th><th>نام</th><th>دسته</th><th>قیمت</th><th>عملیات</th></tr></thead>
            <tbody>
                {% for p in products %}
                <tr>
                    <td>{{ p.id }}</td>
                    <td>{{ p.name }}</td>
                    <td>{{ p.category }}</td>
                    <td>{{ p.price }} تومان</td>
                    <td style="white-space:nowrap;">
                        <a href="/admin_edit_product/{{ p.id }}" class="edit">✏️ ویرایش</a>
                        <a href="/admin_delete_product/{{ p.id }}" class="delete" onclick="return confirm('حذف محصول {{ p.name }}؟')">🗑️ حذف</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        </div></div>
        
        <div class="card"><h2>📋 سفارشات</h2>
        <div style="overflow-x:auto;">
        <table>
            <thead><tr><th>شماره</th><th>کاربر</th><th>مبلغ</th><th>کدها</th><th>تاریخ</th></tr></thead>
            <tbody>
                {% for o in orders %}
                <tr>
                    <td>{{ o.id }}</td>
                    <td>{{ o.user_id }}</td>
                    <td>{{ o.total_price }} تومان</td>
                    <td style="max-width:250px; word-break:break-word;">{{ o.codes }}</td>
                    <td>{{ o.created_at }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        </div></div>
        
        <div class="card"><h2>👥 کاربران</h2>
        <div style="overflow-x:auto;">
        <table>
            <thead><tr><th>شناسه</th><th>نام کاربری</th><th>ایمیل</th><th>ادمین</th></tr></thead>
            <tbody>
                {% for u in users %}
                <tr>
                    <td>{{ u.id }}</td>
                    <td>{{ u.username }}</td>
                    <td>{{ u.email }}</td>
                    <td>{{ u.is_admin }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        </div></div>
        
        <div class="security-buttons" style="text-align: center; margin-top: 20px;">
            <a href="/" style="background:#2ecc71; color:#000;">🏠 صفحه اصلی</a>
            <a href="/admin_panel_logout" style="background:#555; color:white;">🔒 خروج از پنل (فقط رمز دوم)</a>
            <a href="/admin_full_logout" style="background:#e74c3c; color:white;" onclick="return confirm('خروج کامل از حساب ادمین؟')">🚪 خروج کامل از سایت</a>
        </div>
        </body></html>
        ''', products=products, orders=orders, users=users)

    if request.method == 'POST':
        password = request.form.get('panel_password')
        if password == ADMIN_PANEL_EXTRA_PASSWORD:
            session['admin_panel_verified'] = True
            return redirect('/admin_panel')
        else:
            return '''
            <!DOCTYPE html>
            <html dir="rtl">
            <head><meta charset="UTF-8"><title>خطا</title>
            <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/font-face.css" rel="stylesheet">
            <style>body{font-family:'Vazir',Tahoma,sans-serif;background:#0a0a0a;color:#eee;text-align:center;padding-top:100px;}</style>
            </head>
            <body><h3>رمز اشتباه است</h3><a href="/admin_panel">بازگشت</a></body></html>
            '''

    # صفحه ورود رمز دوم (با استایل هماهنگ)
    return '''
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ورود به پنل مدیریت | پیکلمینه</title>
        <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/font-face.css" rel="stylesheet">
        <style>
            * { margin:0; padding:0; box-sizing:border-box; }
            body {
                font-family: 'Vazir', Tahoma, sans-serif;
                background: #0a0a0a;
                color: #eee;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 20px;
            }
            button, input { font-family: 'Vazir', Tahoma, sans-serif; }
            .login-container {
                background: #111;
                border-radius: 30px;
                padding: 40px 30px;
                width: 100%;
                max-width: 450px;
                text-align: center;
                border: 1px solid #2ecc71;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            }
            .login-container h2 {
                color: #2ecc71;
                margin-bottom: 10px;
                font-size: 1.8rem;
            }
            .login-container p {
                color: #aaa;
                margin-bottom: 30px;
                font-size: 0.9rem;
            }
            input {
                width: 100%;
                padding: 14px 18px;
                margin: 10px 0;
                border-radius: 40px;
                border: none;
                background: #1a1a1a;
                color: #fff;
                font-size: 1rem;
                outline: none;
                text-align: center;
                border: 1px solid #2ecc71;
                transition: 0.2s;
            }
            input:focus {
                box-shadow: 0 0 8px #2ecc71;
            }
            button {
                background: #2ecc71;
                color: #000;
                border: none;
                padding: 12px 25px;
                border-radius: 40px;
                font-weight: bold;
                font-size: 1rem;
                cursor: pointer;
                width: 100%;
                margin-top: 10px;
                transition: 0.2s;
            }
            button:hover {
                transform: scale(1.02);
                background: #27ae60;
                box-shadow: 0 5px 15px rgba(46,204,113,0.3);
            }
            .back-link {
                display: inline-block;
                margin-top: 20px;
                color: #2ecc71;
                text-decoration: none;
                font-size: 0.85rem;
            }
            .back-link:hover {
                text-decoration: underline;
            }
            .icon {
                font-size: 48px;
                margin-bottom: 15px;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="icon">🔐</div>
            <h2>ورود به پنل مدیریت</h2>
            <p>لطفاً رمز دوم را وارد کنید</p>
            <form method="POST">
                <input type="password" name="panel_password" placeholder="رمز دسترسی" autofocus>
                <button type="submit">تأیید و ورود</button>
            </form>
            <a href="/" class="back-link">← بازگشت به فروشگاه</a>
        </div>
    </body>
    </html>
    '''

@app.route('/admin_panel_logout')
@login_required
def admin_panel_logout():
    session.pop('admin_panel_verified', None)
    return redirect('/admin_panel')

@app.route('/admin_full_logout')
@login_required
def admin_full_logout():
    logout_user()
    session.pop('admin_panel_verified', None)
    return redirect(url_for('home'))

@app.route('/admin_add_product', methods=['POST'])
@login_required
def admin_add_product():
    if not current_user.is_admin:
        return "دسترسی غیرمجاز", 403
    name = request.form.get('name')
    category = request.form.get('category')
    price = int(request.form.get('price', 0))
    is_free = 'is_free' in request.form
    if name:
        db.session.add(Product(name=name, category=category, price=price, is_free=is_free))
        db.session.commit()
    return redirect('/admin_panel')

@app.route('/admin_delete_product/<int:pid>')
@login_required
def admin_delete_product(pid):
    if not current_user.is_admin:
        return "دسترسی غیرمجاز", 403
    p = Product.query.get(pid)
    if p:
        db.session.delete(p)
        db.session.commit()
    return redirect('/admin_panel')

@app.route('/admin_edit_product/<int:pid>', methods=['GET', 'POST'])
@login_required
def admin_edit_product(pid):
    if not current_user.is_admin:
        return "دسترسی غیرمجاز", 403
    p = Product.query.get(pid)
    if not p:
        return "محصول یافت نشد"
    if request.method == 'POST':
        p.name = request.form.get('name')
        p.category = request.form.get('category')
        p.price = int(request.form.get('price', 0))
        p.is_free = 'is_free' in request.form
        db.session.commit()
        return redirect('/admin_panel')
    return render_template_string('''
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>ویرایش محصول</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/font-face.css" rel="stylesheet">
    <style>
        body{font-family:'Vazir',Tahoma,sans-serif;background:#0a0a0a;color:#eee;padding:20px;}
        button, input { font-family: 'Vazir', Tahoma, sans-serif; }
    </style>
    </head>
    <body><div class="card" style="background:#111;border-radius:20px;padding:20px;border:1px solid #2ecc71;"><h2>ویرایش محصول</h2>
    <form method="POST"><input name="name" value="{{p.name}}" required><select name="category"><option value="skin" {% if p.category=='skin' %}selected{% endif %}>اسکین</option><option value="map" {% if p.category=='map' %}selected{% endif %}>مپ</option><option value="head" {% if p.category=='head' %}selected{% endif %}>هد</option></select><input name="price" type="number" value="{{p.price}}"><label><input type="checkbox" name="is_free" {% if p.is_free %}checked{% endif %}> رایگان</label><button type="submit">ذخیره</button></form><a href="/admin_panel">بازگشت</a></div></body></html>
    ''', p=p)

# -------------------- دیتابیس و نمونه محصولات و ادمین پیش‌فرض --------------------
with app.app_context():
    db.create_all()
    if Product.query.count() == 0:
        sample = [
            Product(name="اسکین فوتوپالیرونالو", category="skin", price=20000),
            Product(name="اسکین مکس ورشتاب", category="skin", price=20000),
            Product(name="هد ازهای اندر", category="head", price=10000),
            Product(name="مپ خانه مدرن", category="map", price=40000),
            Product(name="مپ جزیره فانتزی", category="map", price=50000),
            Product(name="2 مپ رایگان", category="map", price=0, is_free=True),
            Product(name="10 اسکین رایگان", category="skin", price=0, is_free=True),
        ]
        db.session.add_all(sample)
        db.session.commit()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='mr.javaheriam@gmail.com', password=hashlib.md5('adminjavahri'.encode()).hexdigest(), is_admin=True)
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, port=5000)