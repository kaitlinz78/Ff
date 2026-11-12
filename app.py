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
    return """<!doctype html><html lang="ru"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Cache-Control" content="no-store"><script src="https://telegram.org/js/telegram-web-app.js"></script><style>body{font-family:system-ui;background:#0b0b0c;color:#f5f5f5;margin:0;padding:18px}.card{background:#1b1b1d;border:1px solid #444;border-radius:22px;padding:22px;max-width:520px;margin:24px auto}h1{margin-top:0}input{box-sizing:border-box;padding:12px;border:1px solid #666;background:#101012;color:#fff;border-radius:12px;width:100%;margin:7px 0 16px;font-size:18px}input[readonly]{color:#aaa;background:#29292b}b{font-size:24px}.muted{color:#aaa;font-size:13px}.warn{color:#f2cb7a}label{display:block}</style><div class="card"><h1>Spread Monitor</h1><p class="warn" id="status">Ожидание проверенных котировок · расчёт недоступен</p><label>Цифра Маркет · цена покупки USDT, ₽</label><input id="ask" readonly placeholder="Нет котировки" aria-label="Курс Цифры"><label>Рапира · курс обмена, ₽/USDT</label><input id="rap" readonly placeholder="Нет котировки" aria-label="Курс Рапиры"><p class="muted">Курсы загружаются автоматически и не редактируются.</p><label>Бюджет, ₽</label><input id="amount" type="number" min="0" value="0" step="1000"><p>Чистая прибыль: <b id="profit">—</b></p><p>Чистый спред: <b id="pct">—</b></p><hr><h2>Дополнительно: калькулятор USDT</h2><label>Объём, USDT</label><input id="usdt" type="number" min="0" value="0" step="100"><p>Стоимость покупки: <b id="cost">—</b></p><p>Выручка после комиссии: <b id="revenue">—</b></p><p>Чистая прибыль: <b id="usdtprofit">—</b></p><p>Чистая прибыль в USDT: <b id="usdtprofitcoin">—</b></p><p>Доходность: <b id="usdtpct">—</b></p><small class="muted">Предварительные комиссии: Цифра 1,5%, Рапира 0,4%. Результат будет доступен только после подключения и проверки обоих реальных источников. Без подтверждённой ликвидности расчёт ориентировочный.</small></div><script>let rates=null;const fmt=(v,unit)=>Number.isFinite(v)?v.toLocaleString('ru-RU',{maximumFractionDigits:2})+' '+unit:'—';function calc(){const n=Number(amount.value),u=Number(usdt.value);if(!rates){for(const id of ['profit','pct','cost','revenue','usdtprofit','usdtprofitcoin','usdtpct'])document.getElementById(id).textContent='—';return}const a=rates.ask,r=rates.rap;const rubOut=n*.985/a*r*.996;profit.textContent=n>0?fmt(rubOut-n,'₽'):'—';pct.textContent=fmt(((.985/a*r*.996)-1)*100,'%');const buy=u*a/.985,sell=u*r*.996,net=sell-buy;cost.textContent=u>0?fmt(buy,'₽'):'—';revenue.textContent=u>0?fmt(sell,'₽'):'—';usdtprofit.textContent=u>0?fmt(net,'₽'):'—';usdtprofitcoin.textContent=u>0?fmt(net/(a/.985),'USDT'):'—';usdtpct.textContent=u>0?fmt(net/buy*100,'%'):'—'}async function refresh(){try{const t=window.Telegram?.WebApp?.initData||'';const res=await fetch('/api/quotes',{headers:{'X-Telegram-Init-Data':t},cache:'no-store'});if(!res.ok)throw Error('Котировки пока недоступны');const d=await res.json();if(d.connected===true&&d.verified===true&&Number(d.cifra_ask)>0&&Number(d.rapira_exchange_rate)>0){rates={ask:Number(d.cifra_ask),rap:Number(d.rapira_exchange_rate)};ask.value=rates.ask;rap.value=rates.rap;status.textContent='Проверенные котировки · обновление каждые 10 секунд'}else throw Error('Ожидание проверенных котировок')}catch(e){rates=null;ask.value='';rap.value='';status.textContent='Котировки не подключены · расчёт недоступен'}calc()}amount.oninput=calc;usdt.oninput=calc;refresh();setInterval(refresh,10000);</script></html>"""
@app.get("/health")
def health(): return {"ok":True,"quotes_connected":False,"bot_configured":bool(TOKEN)}
@app.get("/api/quotes")
def quotes(x_telegram_init_data:str=Header(default="")):
    verify(x_telegram_init_data)
    return {"connected":False,"reason":"Verified exchange adapters not configured"}

# Public Rapira SPOT reference only; NOT the RUB→USDT "Exchange" quote.
@app.get("/api/rapira-spot-reference")
async def rapira_spot_reference():
    import httpx
    from fastapi import HTTPException
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response=await client.get("https://api.rapira.net/open/market/rates",headers={"Accept":"application/json"})
            response.raise_for_status()
            payload=response.json()
        items=payload.get("data",[]) if isinstance(payload,dict) else payload
        item=next((x for x in items if x.get("symbol")=="USDT/RUB"),None)
        if not item: raise ValueError("USDT/RUB unavailable")
        return {"source":"Rapira public spot API","kind":"spot_reference_only","is_exchange_quote":False,
                "symbol":"USDT/RUB","bid":item.get("bidPrice"),"ask":item.get("askPrice"),
                "warning":"Not the RUB→USDT Exchange quote; do not use for spread alerts"}
    except Exception:
        raise HTTPException(503,"Rapira public spot rate unavailable")
