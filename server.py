import json, os, mimetypes, time, threading, re
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from database import init_db, save_generation, recent_generations, get_settings, update_settings, stats, set_favorite, delete_generation, get_generation
from ai_service import generate, TOOLS, provider_status, test_provider

ROOT=Path(__file__).resolve().parent; HOST="127.0.0.1"; PORT=int(os.getenv("PORT","5000"))
RATE_LOCK=threading.Lock(); RATE_LOG={}; RATE_LIMIT=25; WINDOW=60

def load_env():
    env=ROOT/'.env'
    if not env.exists(): return
    for raw in env.read_text(encoding='utf-8').splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1); os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))

def allowed(ip):
    now=time.time()
    with RATE_LOCK:
        hits=[t for t in RATE_LOG.get(ip,[]) if now-t<WINDOW]
        if len(hits)>=RATE_LIMIT: RATE_LOG[ip]=hits; return False
        hits.append(now); RATE_LOG[ip]=hits; return True

class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args): print(f"[{self.log_date_time_string()}] {fmt%args}")
    def send_json(self,payload,status=200):
        body=json.dumps(payload,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def read_json(self):
        length=int(self.headers.get('Content-Length','0') or 0)
        if length>400000: raise ValueError('Request too large')
        raw=self.rfile.read(length); return json.loads(raw.decode('utf-8') or '{}')
    def do_GET(self):
        path=urlparse(self.path).path; q=parse_qs(urlparse(self.path).query)
        if path=='/api/health': return self.send_json({'ok':True,'service':'RealAI Toolkit','version':'2.0','db':'sqlite','providers':provider_status(),'tools':len(TOOLS)})
        if path=='/api/tools': return self.send_json({'ok':True,'tools':TOOLS})
        if path=='/api/stats': return self.send_json({'ok':True,'stats':stats()})
        if path=='/api/history': return self.send_json({'ok':True,'items':recent_generations(int(q.get('limit',['40'])[0]), q.get('tool',[None])[0], q.get('favorites',['0'])[0]=='1')})
        if path.startswith('/api/history/'):
            try: gid=int(path.rsplit('/',1)[1])
            except: return self.send_json({'ok':False,'error':'Bad id'},400)
            item=get_generation(gid)
            return self.send_json({'ok':bool(item),'item':item},200 if item else 404)
        if path=='/api/settings': return self.send_json({'ok':True,'settings':get_settings()})
        if path=='/': return self.serve(ROOT/'templates'/'index.html','text/html; charset=utf-8')
        rel=path.lstrip('/'); target=(ROOT/rel).resolve()
        try: target.relative_to(ROOT.resolve())
        except ValueError: return self.send_json({'ok':False,'error':'Not found'},404)
        if target.is_file(): return self.serve(target,mimetypes.guess_type(str(target))[0] or 'application/octet-stream')
        return self.send_json({'ok':False,'error':'Not found'},404)
    def serve(self,path,ctype):
        if not path.exists(): return self.send_json({'ok':False,'error':'Not found'},404)
        body=path.read_bytes(); self.send_response(200); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        path=urlparse(self.path).path
        if path=='/api/ai':
            if not allowed(self.client_address[0]): return self.send_json({'ok':False,'error':'Rate limit reached. Try again in a minute.'},429)
            started=time.perf_counter()
            try:
                d=self.read_json(); tool=str(d.get('tool','')).strip(); mode=str(d.get('mode','professional')).strip() or 'professional'; text=str(d.get('input',''))
                out,provider=generate(tool,mode,text); latency=round((time.perf_counter()-started)*1000); gid=save_generation(tool,mode,text,out,provider,latency)
                return self.send_json({'ok':True,'id':gid,'output':out,'provider':provider,'latency_ms':latency})
            except ValueError as e: return self.send_json({'ok':False,'error':str(e)},400)
            except Exception as e: return self.send_json({'ok':False,'error':str(e)},500)
        if path=='/api/provider/test':
            try:
                d=self.read_json(); name=str(d.get('provider','')).strip().lower(); started=time.perf_counter(); msg=test_provider(name); return self.send_json({'ok':True,'provider':name,'message':msg,'latency_ms':round((time.perf_counter()-started)*1000)})
            except Exception as e: return self.send_json({'ok':False,'error':str(e)},400)
        return self.send_json({'ok':False,'error':'Not found'},404)
    def do_PUT(self):
        path=urlparse(self.path).path
        if path=='/api/settings':
            try: d=self.read_json(); return self.send_json({'ok':True,'settings':update_settings(d.get('display_name'),d.get('theme'),d.get('default_tool'))})
            except Exception as e: return self.send_json({'ok':False,'error':str(e)},400)
        if path.startswith('/api/history/') and path.endswith('/favorite'):
            try: gid=int(path.split('/')[3]); d=self.read_json(); ok=set_favorite(gid,bool(d.get('favorite'))); return self.send_json({'ok':ok})
            except Exception as e: return self.send_json({'ok':False,'error':str(e)},400)
        return self.send_json({'ok':False,'error':'Not found'},404)
    def do_DELETE(self):
        path=urlparse(self.path).path
        if path.startswith('/api/history/'):
            try: gid=int(path.rsplit('/',1)[1]); ok=delete_generation(gid); return self.send_json({'ok':ok},200 if ok else 404)
            except Exception as e: return self.send_json({'ok':False,'error':str(e)},400)
        return self.send_json({'ok':False,'error':'Not found'},404)

if __name__=='__main__':
    load_env(); init_db(); print(f'RealAI Toolkit v2 running at http://{HOST}:{PORT}'); ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
