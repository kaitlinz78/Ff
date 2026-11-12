import os, hmac, hashlib, json, time
from urllib.parse import parse_qsl
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
app=FastAPI()
TOKEN=os.getenv("BOT_TOKEN","")
ALLOWED={int(x) for x in os.getenv("ALLOWED_TELEGRAM_IDS","").split(",") if x.strip().isdigit()}
def verify(raw):
    if not TOKEN: raise HTTPException(503,"Bot not configured")
    data=dict(parse_qsl(raw,keep_blank_values=True))
    supplied=data.pop("hash","")
    try:
        if abs(time.time()-int(data["auth_date"]))>3600: raise ValueError()
        secret=hmac.new(b"WebAppData",TOKEN.encode(),hashlib.sha256).digest()
        check="\n".join(f"{k}={v}" for k,v in sorted(data.items()))
        expected=hmac.new(secret,check.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(supplied,expected): raise ValueError()
        user=json.loads(data["user"])
        if user["id"] not in ALLOWED: raise HTTPException(403,"Not allowed")
        return user
    except HTTPException: raise
    except Exception: raise HTTPException(401,"Invalid Telegram session")
@app.get("/",response_class=HTMLResponse)
def home():
    return """<!doctype html><html lang="ru"><meta name="viewport" content="width=device-width, initial-scale=1"><script src="https://telegram.org/js/telegram-web-app.js"></script><style>body{font-family:system-ui;background:linear-gradient(145deg,#c5f8f3,#e5f5ff);color:#123c48;margin:0;padding:24px}.card{background:white;border-radius:22px;padding:24px;max-width:520px;margin:30px auto;box-shadow:0 8px 30px #87c8c444}h1{margin-top:0}input{padding:12px;border:1px solid #b7dadc;border-radius:12px;width:90%;margin:6px 0 14px}b{font-size:26px}</style><div class="card"><h1>Spread Monitor</h1><p id="status">Демо · котировки не подключены</p><label>Цифра Маркет ask, ₽/USDT</label><input id="ask" type="number" value="83.17" step=".01"><label>Рапира RUB→USDT, ₽/USDT</label><input id="rap" type="number" value="86.33" step=".01"><label>Бюджет, ₽</label><input id="amount" type="number" value="600000"><p>Чистая прибыль: <b id="profit"></b></p><hr><h2>Дополнительно: калькулятор по USDT</h2><label>Сумма сделки, USDT</label><input id="usdt" type="number" min="0" value="30000" step="100"><p>Затраты на покупку с комиссией: <b id="cost"></b></p><p>Выручка после комиссии Рапиры: <b id="revenue"></b></p><p>Чистая прибыль: <b id="usdtprofit"></b></p><p>Доходность: <b id="usdtpct"></b></p><p>Чистый спред: <b id="pct"></b></p><small>Примерные комиссии: Цифра 1,5%, Рапира 0,4%. Демо-цены не являются текущими котировками. Сделки не выполняются.</small></div><script>function calc(){let a=+ask.value,r=+rap.value,n=+amount.value;let cash=n*.985/a*r*.996;profit.textContent=isFinite(cash)?(cash-n).toLocaleString('ru-RU',{maximumFractionDigits:0})+' ₽':'—';pct.textContent=isFinite(cash)?((cash/n-1)*100).toFixed(2)+'%':'—'}function calcUsd(){let u=+usdt.value,a=+ask.value,r=+rap.value;let buy=u*a/.985,sell=u*r*.996,net=sell-buy;const rub=x=>isFinite(x)?x.toLocaleString('ru-RU',{maximumFractionDigits:0})+' ₽':'—';cost.textContent=rub(buy);revenue.textContent=rub(sell);usdtprofit.textContent=rub(net);usdtpct.textContent=buy>0?((net/buy)*100).toFixed(2)+'%':'—'}document.querySelectorAll('input').forEach(x=>x.oninput=()=>{calc();calcUsd()});calc();calcUsd();</script></html>"""
@app.get("/health")
def health(): return {"ok":True,"quotes_connected":False,"bot_configured":bool(TOKEN)}
@app.get("/api/quotes")
def quotes(x_telegram_init_data:str=Header(default="")):
    verify(x_telegram_init_data)
    return {"connected":False,"reason":"Verified exchange adapters not configured"}
