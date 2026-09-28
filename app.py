import os, json, hmac, hashlib, base64, time, secrets, urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Float, Integer, Text, Boolean, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from dotenv import load_dotenv

load_dotenv()
BASE=Path(__file__).parent
DATABASE_URL=os.getenv('DATABASE_URL','sqlite:///./cyberpulse.db')
if DATABASE_URL.startswith('postgres://'): DATABASE_URL='postgresql+psycopg://'+DATABASE_URL[len('postgres://'):]
engine=create_engine(DATABASE_URL, connect_args={'check_same_thread':False} if DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)

class Base(DeclarativeBase): pass
class Product(Base):
    __tablename__='products'
    id: Mapped[int]=mapped_column(Integer, primary_key=True)
    name: Mapped[str]=mapped_column(String(160)); price_usd: Mapped[float]=mapped_column(Float)
    price_usd_max: Mapped[float|None]=mapped_column(Float, nullable=True); category: Mapped[str]=mapped_column(String(40))
    img: Mapped[str]=mapped_column(String(255)); desc: Mapped[str]=mapped_column(Text); full_desc: Mapped[str]=mapped_column(Text)
    specs_json: Mapped[str]=mapped_column(Text, default='[]'); active: Mapped[bool]=mapped_column(Boolean, default=True)
class Order(Base):
    __tablename__='orders'
    id: Mapped[int]=mapped_column(Integer, primary_key=True, autoincrement=True)
    number: Mapped[str]=mapped_column(String(40), unique=True, index=True)
    created_at: Mapped[str]=mapped_column(String(40)); status: Mapped[str]=mapped_column(String(30), default='new')
    full_name: Mapped[str]=mapped_column(String(160)); phone: Mapped[str]=mapped_column(String(50)); email: Mapped[str]=mapped_column(String(160))
    delivery: Mapped[str]=mapped_column(String(30)); city: Mapped[str]=mapped_column(String(120)); address: Mapped[str]=mapped_column(String(300)); zip: Mapped[str]=mapped_column(String(30)); payment: Mapped[str]=mapped_column(String(30)); comment: Mapped[str]=mapped_column(Text, default='')
    items_json: Mapped[str]=mapped_column(Text); subtotal_usd: Mapped[float]=mapped_column(Float); delivery_usd: Mapped[float]=mapped_column(Float); total_usd: Mapped[float]=mapped_column(Float)
Base.metadata.create_all(engine)

SEED_PRODUCTS = [(1, 'Flipper Zero', 390, None, 'devices', 'flipper-zero.png', 'Универсальный инструмент для исследования безопасности. Оригинал, новый, запечатанный.', 'Flipper Zero — универсальный инструмент для исследования безопасности.', ['SUB-GHZ: анализ радиосигналов', 'NFC / RFID: чтение и эмуляция', 'IR: управление устройствами', 'Bluetooth LE', 'GPIO и USB']), (2, 'HackRF One', 590, None, 'devices', 'hackrf-one.png', 'Software Defined Radio (SDR) платформа 1 МГц–6 ГГц.', 'HackRF One — широкополосная SDR-платформа.', ['1 МГц – 6 ГГц', 'Half-duplex SDR', 'USB 2.0', 'SMA']), (3, 'HackRF One PortaPack H2', 590, None, 'devices', 'hackrf-portapack.png', 'Портативная SDR-платформа с PortaPack H2.', 'HackRF One с PortaPack H2 для автономной работы.', ['1 МГц – 6 ГГц', 'LCD экран', 'SMA', 'microSD / USB']), (4, 'uConsole', 950, 1240, 'devices', 'uconsole.png', 'Портативная Linux-консоль. Цена зависит от комплектации.', 'uConsole — портативная модульная Linux-консоль.', ['Linux', 'Модульная конструкция', 'Клавиатура и экран', 'Цена зависит от комплектации']), (5, 'Raspberry Pi 4 (8GB)', 120, None, 'devices', 'raspberry-pi4.png', 'Одноплатный компьютер с 8 ГБ RAM.', 'Raspberry Pi 4 Model B, 8 ГБ.', ['8 GB RAM', 'ARM Cortex-A72', 'USB 3.0', 'Wi‑Fi + Bluetooth']), (6, 'WiFi Pineapple', 590, None, 'devices', 'wifi-pineapple.png', 'Платформа для авторизованного аудита Wi‑Fi сетей.', 'WiFi Pineapple — инструмент для тестирования беспроводных сетей.', ['Аудит Wi‑Fi', 'Мониторинг', 'PineAP', 'Веб-интерфейс']), (7, 'CC1101 модуль', 120, None, 'modules', 'cc1101.png', 'Дополнительный Sub‑GHz модуль для Flipper Zero.', 'CC1101 модуль для лабораторных и авторизованных исследований радиосвязи.', ['Sub‑GHz', 'Внешняя антенна', 'GPIO', 'Для Flipper Zero']), (8, '3-в-1 ESP32 + NRF24 + CC1101', 250, None, 'modules', 'esp32-marauder.png', 'Универсальный модуль 3-в-1 для Flipper Zero.', 'Комбинированный модуль ESP32 + NRF24 + CC1101.', ['ESP32', 'NRF24', 'CC1101', 'GPIO']), (9, 'ESP32 DIV', 160, None, 'devices', 'esp32-multitool.png', 'Портативное устройство на ESP32 для лабораторных исследований.', 'ESP32 DIV — многофункциональная платформа на ESP32.', ['ESP32', 'Wi‑Fi', 'Bluetooth LE', 'USB']), (10, 'NRF24 для Flipper Zero', 110, None, 'modules', 'nrf24.png', 'Модуль nRF24L01+ для Flipper Zero.', 'NRF24 для исследований 2.4 ГГц в собственной лаборатории.', ['2.4 GHz', 'Внешняя антенна', 'GPIO', 'Flipper Zero']), (11, 'SUB-GHZ PRO модуль', 150, None, 'modules', 'subghz-pro.png', 'Расширение Sub‑GHz для Flipper Zero.', 'SUB-GHZ PRO для лабораторных исследований Sub‑GHz.', ['Sub‑GHz', 'Приём/передача', 'GPIO', 'Внешняя антенна']), (12, 'ESP32 Wi‑Fi Board', 110, 120, 'modules', 'esp32-wifi.png', 'Wi‑Fi Board для Flipper Zero с поддержкой Marauder.', 'ESP32 Wi‑Fi Board для авторизованного тестирования Wi‑Fi.', ['2.4 GHz', 'ESP32', 'Marauder', 'GPIO']), (13, 'Кастомная прошивка', 50, None, 'firmware', 'custom-firmware.png', 'Установка кастомной прошивки на Flipper Zero.', 'Услуга установки выбранной совместимой прошивки.', ['Установка', 'Настройка', 'Проверка', 'Поддержка']), (14, 'BadUSB для Flipper Zero', 80, None, 'accessories', 'badusb.png', 'Аксессуар для автоматизации разрешённых USB-сценариев.', 'BadUSB для лабораторной автоматизации и обучения.', ['USB HID', 'Автоматизация', 'Учебные сценарии', 'Тестовая среда'])]
def seed():
    with Session(engine) as db:
        if db.scalar(select(func.count(Product.id)))==0:
            for x in SEED_PRODUCTS:
                i,n,p,pmax,c,img,d,fd,s=x
                db.add(Product(id=i,name=n,price_usd=p,price_usd_max=pmax,category=c,img=img,desc=d,full_desc=fd,specs_json=json.dumps(s,ensure_ascii=False),active=True))
            db.commit()
seed()

app=FastAPI(title='CyberPulse.it Store', docs_url=None, redoc_url=None)
app.mount('/static', StaticFiles(directory=BASE/'static'), name='static')
SESSION_SECRET=os.getenv('SESSION_SECRET') or secrets.token_hex(32)
ADMIN_USERNAME=os.getenv('ADMIN_USERNAME','admin'); ADMIN_PASSWORD=os.getenv('ADMIN_PASSWORD','CHANGE_ME_LONG_RANDOM_PASSWORD')
login_attempts={}

def product_dict(p): return {'id':p.id,'name':p.name,'price_usd':p.price_usd,'price_usd_max':p.price_usd_max,'category':p.category,'img':p.img,'desc':p.desc,'fullDesc':p.full_desc,'specs':json.loads(p.specs_json or '[]'),'active':p.active}
def sign_session(exp):
    payload=f'{exp}'.encode(); sig=hmac.new(SESSION_SECRET.encode(),payload,hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload+b'.'+sig).decode()
def is_admin(request:Request):
    token=request.cookies.get('cp_admin');
    if not token: return False
    try:
        raw=base64.urlsafe_b64decode(token.encode()); payload,sig=raw.split(b'.',1)
        if not hmac.compare_digest(sig,hmac.new(SESSION_SECRET.encode(),payload,hashlib.sha256).digest()): return False
        return int(payload.decode())>int(time.time())
    except Exception:return False
def require_admin(request:Request):
    if not is_admin(request): raise HTTPException(401,'Unauthorized')
    return True

class LoginIn(BaseModel): username:str=Field(max_length=100); password:str=Field(max_length=200)
class CartItem(BaseModel): id:int; quantity:int=Field(ge=1,le=20)
class OrderIn(BaseModel):
    fullName:str=Field(min_length=2,max_length=160); phone:str=Field(min_length=5,max_length=50); email:str=Field(min_length=3,max_length=160)
    delivery:str; city:str=Field(min_length=1,max_length=120); address:str=Field(min_length=2,max_length=300); zip:str=Field(min_length=1,max_length=30)
    payment:str; comment:str=Field(default='',max_length=1000); items:list[CartItem]
class ProductIn(BaseModel):
    name:str=Field(min_length=2,max_length=160); price_usd:float=Field(gt=0,le=100000); price_usd_max:float|None=None; category:str; img:str=Field(max_length=255); desc:str=Field(max_length=1000); fullDesc:str=Field(max_length=5000); specs:list[str]=[]; active:bool=True
class StatusIn(BaseModel): status:str

@app.middleware('http')
async def headers(request,call_next):
    r=await call_next(request)
    r.headers['X-Content-Type-Options']='nosniff'; r.headers['X-Frame-Options']='DENY'; r.headers['Referrer-Policy']='strict-origin-when-cross-origin'; r.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    return r
@app.get('/api/health')
def health(): return {'ok':True}
@app.get('/api/products')
def products():
    with Session(engine) as db:return [product_dict(p) for p in db.scalars(select(Product).where(Product.active==True).order_by(Product.id)).all()]
@app.get('/api/products/{pid}')
def product(pid:int):
    with Session(engine) as db:
        p=db.get(Product,pid)
        if not p or not p.active: raise HTTPException(404,'Product not found')
        return product_dict(p)
@app.post('/api/admin/login')
def login(data:LoginIn, request:Request, response:Response):
    ip=request.client.host if request.client else 'unknown'; now=time.time(); arr=[t for t in login_attempts.get(ip,[]) if now-t<300]
    if len(arr)>=8: raise HTTPException(429,'Too many attempts')
    ok=hmac.compare_digest(data.username,ADMIN_USERNAME) and hmac.compare_digest(data.password,ADMIN_PASSWORD)
    if not ok:
        arr.append(now); login_attempts[ip]=arr; raise HTTPException(401,'Invalid credentials')
    login_attempts.pop(ip,None); response.set_cookie('cp_admin',sign_session(int(now+7200)),httponly=True,samesite='strict',secure=os.getenv('COOKIE_SECURE','0')=='1',max_age=7200,path='/')
    return {'ok':True}
@app.post('/api/admin/logout')
def logout(response:Response): response.delete_cookie('cp_admin',path='/'); return {'ok':True}
@app.get('/api/admin/me')
def me(request:Request): return {'authenticated':is_admin(request)}
@app.get('/api/admin/products')
def admin_products(_:bool=Depends(require_admin)):
    with Session(engine) as db:return [product_dict(p) for p in db.scalars(select(Product).order_by(Product.id)).all()]
@app.post('/api/admin/products')
def add_product(data:ProductIn,_:bool=Depends(require_admin)):
    with Session(engine) as db:
        p=Product(name=data.name,price_usd=data.price_usd,price_usd_max=data.price_usd_max,category=data.category,img=data.img,desc=data.desc,full_desc=data.fullDesc,specs_json=json.dumps(data.specs,ensure_ascii=False),active=data.active); db.add(p);db.commit();db.refresh(p);return product_dict(p)
@app.put('/api/admin/products/{pid}')
def edit_product(pid:int,data:ProductIn,_:bool=Depends(require_admin)):
    with Session(engine) as db:
        p=db.get(Product,pid)
        if not p: raise HTTPException(404,'Not found')
        for k,v in {'name':data.name,'price_usd':data.price_usd,'price_usd_max':data.price_usd_max,'category':data.category,'img':data.img,'desc':data.desc,'full_desc':data.fullDesc,'specs_json':json.dumps(data.specs,ensure_ascii=False),'active':data.active}.items():setattr(p,k,v)
        db.commit();return product_dict(p)
@app.delete('/api/admin/products/{pid}')
def delete_product(pid:int,_:bool=Depends(require_admin)):
    with Session(engine) as db:
        p=db.get(Product,pid)
        if not p: raise HTTPException(404,'Not found')
        p.active=False;db.commit();return {'ok':True}

DELIVERY={'cdek':5.0,'dhl':15.0}
def notify_telegram(o,items):
    token=os.getenv('TELEGRAM_BOT_TOKEN'); chat=os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat:return
    lines='\n'.join(f"• {i['name']} × {i['quantity']} = ${i['line_total']:.2f}" for i in items)
    text=f"🛒 Новый заказ {o.number}\n\n{lines}\n\nИтого: ${o.total_usd:.2f}\nКлиент: {o.full_name}\nТелефон: {o.phone}\nГород: {o.city}\nДоставка: {o.delivery}\nОплата: {o.payment}"
    data={'chat_id':chat,'text':text}; topic=os.getenv('TELEGRAM_TOPIC_ID')
    if topic:data['message_thread_id']=topic
    try: urllib.request.urlopen(urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage',data=urllib.parse.urlencode(data).encode()),timeout=5).read()
    except Exception as e: print('Telegram notification failed:',e)
@app.post('/api/orders')
def create_order(data:OrderIn):
    if data.delivery not in DELIVERY or data.payment not in {'card','crypto'}: raise HTTPException(400,'Invalid checkout option')
    if not data.items or len(data.items)>30: raise HTTPException(400,'Cart is empty or too large')
    with Session(engine) as db:
        resolved=[];subtotal=0.0
        for ci in data.items:
            p=db.get(Product,ci.id)
            if not p or not p.active: raise HTTPException(400,f'Product {ci.id} unavailable')
            line=round(p.price_usd*ci.quantity,2); subtotal+=line;resolved.append({'id':p.id,'name':p.name,'quantity':ci.quantity,'price_usd':p.price_usd,'line_total':line})
        delivery=DELIVERY[data.delivery]; total=round(subtotal+delivery,2); number='CP-'+datetime.now().strftime('%y%m%d')+'-'+secrets.token_hex(3).upper()
        o=Order(number=number,created_at=datetime.now(timezone.utc).isoformat(),status='new',full_name=data.fullName.strip(),phone=data.phone.strip(),email=data.email.strip(),delivery=data.delivery,city=data.city.strip(),address=data.address.strip(),zip=data.zip.strip(),payment=data.payment,comment=data.comment.strip(),items_json=json.dumps(resolved,ensure_ascii=False),subtotal_usd=round(subtotal,2),delivery_usd=delivery,total_usd=total)
        db.add(o);db.commit();db.refresh(o);notify_telegram(o,resolved);return {'ok':True,'orderNumber':number,'subtotal_usd':o.subtotal_usd,'delivery_usd':delivery,'total_usd':total}
@app.get('/api/admin/orders')
def orders(_:bool=Depends(require_admin)):
    with Session(engine) as db:
        rows=db.scalars(select(Order).order_by(Order.id.desc())).all();return [{'id':o.id,'number':o.number,'created_at':o.created_at,'status':o.status,'fullName':o.full_name,'phone':o.phone,'email':o.email,'delivery':o.delivery,'city':o.city,'address':o.address,'zip':o.zip,'payment':o.payment,'comment':o.comment,'items':json.loads(o.items_json),'subtotal_usd':o.subtotal_usd,'delivery_usd':o.delivery_usd,'total_usd':o.total_usd} for o in rows]
@app.patch('/api/admin/orders/{oid}/status')
def order_status(oid:int,data:StatusIn,_:bool=Depends(require_admin)):
    allowed={'new','confirmed','paid','shipped','completed','cancelled'}
    if data.status not in allowed:raise HTTPException(400,'Invalid status')
    with Session(engine) as db:
        o=db.get(Order,oid)
        if not o:raise HTTPException(404,'Not found')
        o.status=data.status;db.commit();return {'ok':True}

@app.get('/')
def home():return FileResponse(BASE/'static/index.html')
@app.get('/{page}.html')
def pages(page:str):
    if page not in {'index','product','checkout','success','admin'}:raise HTTPException(404)
    return FileResponse(BASE/'static'/f'{page}.html')
