"""Agent 执行器：工具循环 + 全量计量 + 限流重试。"""
import json, time, pathlib, subprocess, sys, threading, urllib.request, urllib.error
from _key import load

sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).resolve().parent
CTX  = HERE / "_context"
KEY, _ = load()
URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_ITERS = 40

# ---------- 限流：免费端点 20 次/分钟，留余量走 16 ----------
class Throttle:
    def __init__(self, per_min=16):
        self.gap = 60.0 / per_min; self.last = 0.0; self.lock = threading.Lock()
    def wait(self):
        with self.lock:
            d = self.gap - (time.time() - self.last)
            if d > 0: time.sleep(d)
            self.last = time.time()
THROTTLE = Throttle()

# ---------- 工具 ----------
TOOLS = [
 {"type":"function","function":{"name":"list_materials",
  "description":"列出可用的微软财报材料文件及其字符数。",
  "parameters":{"type":"object","properties":{},"required":[]}}},
 {"type":"function","function":{"name":"read_material",
  "description":"读取材料文件的一段文本。文件很大时分段读取。",
  "parameters":{"type":"object","properties":{
     "name":{"type":"string","description":"文件名，来自 list_materials"},
     "offset":{"type":"integer","description":"起始字符位置，默认 0"},
     "length":{"type":"integer","description":"读取长度，默认 20000，最大 60000"}},
   "required":["name"]}}},
 {"type":"function","function":{"name":"search_material",
  "description":"在某个材料文件里搜索关键词，返回命中位置及上下文。",
  "parameters":{"type":"object","properties":{
     "name":{"type":"string"},"query":{"type":"string"},
     "max_hits":{"type":"integer","description":"默认 5"}},
   "required":["name","query"]}}},
 {"type":"function","function":{"name":"run_python",
  "description":"在工作目录执行 Python 代码，返回 stdout/stderr。可用 openpyxl。材料在 ./materials/ 下。产出文件写到工作目录。",
  "parameters":{"type":"object","properties":{
     "code":{"type":"string"}},"required":["code"]}}},
]

def t_list_materials(workdir):
    return "\n".join(f"{p.name}  ({len(p.read_text(encoding='utf-8')):,} 字符)"
                     for p in sorted(CTX.glob("*.txt")))

def t_read_material(workdir, name, offset=0, length=20000):
    p = CTX / name
    if not p.exists(): return f"错误：没有文件 {name}"
    txt = p.read_text(encoding="utf-8")
    length = max(1, min(int(length), 60000)); offset = max(0, int(offset))
    seg = txt[offset:offset+length]
    return f"[{name} 第 {offset}–{offset+len(seg)} 字符，共 {len(txt)}]\n{seg}"

def t_search_material(workdir, name, query, max_hits=5):
    p = CTX / name
    if not p.exists(): return f"错误：没有文件 {name}"
    txt = p.read_text(encoding="utf-8"); out=[]; start=0
    for _ in range(int(max_hits)):
        i = txt.find(query, start)
        if i < 0: break
        out.append(f"[位置 {i}]\n...{txt[max(0,i-400):i+400]}...")
        start = i + 1
    return "\n\n".join(out) if out else f"在 {name} 中未找到 “{query}”"

def t_run_python(workdir, code):
    wd = workdir.resolve()
    f = wd / f"_step_{int(time.time()*1000)}.py"
    f.write_text(code, encoding="utf-8")
    try:
        r = subprocess.run([sys.executable, str(f)], cwd=str(wd),
                           capture_output=True, text=True, timeout=180,
                           encoding="utf-8", errors="replace")
        out = (r.stdout or "")[-6000:]; err = (r.stderr or "")[-3000:]
        return f"exit={r.returncode}\n--- stdout ---\n{out}\n--- stderr ---\n{err}"
    except subprocess.TimeoutExpired:
        return "错误：执行超时（180 秒）"

DISPATCH = {"list_materials":t_list_materials, "read_material":t_read_material,
            "search_material":t_search_material, "run_python":t_run_python}

# ---------- API ----------
def post(payload, tries=5):
    for a in range(tries):
        THROTTLE.wait()
        req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
              headers={"Authorization":"Bearer "+KEY,"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r), None
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            if e.code in (429,500,502,503,524) and a < tries-1:
                time.sleep(min(60, 5*(2**a)))
                continue
            return None, f"HTTP {e.code}: {body}"
        except Exception as e:
            if a < tries-1: time.sleep(5*(2**a)); continue
            return None, f"{type(e).__name__}: {e}"
    return None, "重试耗尽"

def run(model, task_id, prompt, run_idx, outroot, max_tokens=8000, use_tools=True):
    workdir = outroot.resolve() / f"{task_id}_{model.split('/')[-1].replace(':','_')}_r{run_idx}"
    workdir.mkdir(parents=True, exist_ok=True)
    md = workdir/"materials"; md.mkdir(exist_ok=True)
    import shutil
    src = HERE.parent/"materials"/"FinancialStatementFY26Q4.xlsx"
    if src.exists() and not (md/src.name).exists(): shutil.copy2(src, md/src.name)
    msgs = [{"role":"user","content":prompt}]
    log = {"model":model,"task":task_id,"run":run_idx,"iters":0,"tool_calls":0,
           "max_tokens":max_tokens,"use_tools":use_tools,
           "prompt_tokens":0,"completion_tokens":0,"reasoning_tokens":0,"cost":0.0,
           "http_errors":[],"retries_429":0,"hit_length_cap":False,
           "elapsed":0.0,"final":None,"trace":[]}
    t0 = time.time()
    for it in range(MAX_ITERS):
        log["iters"] = it+1
        body = {"model":model,"messages":msgs,
                "temperature":1,"top_p":0.95,"max_tokens":max_tokens}
        if use_tools: body["tools"] = TOOLS
        d, err = post(body)
        if err:
            log["http_errors"].append(err); break
        if not (d or {}).get("choices"):
            log["http_errors"].append(f"响应缺少 choices: {str(d)[:200]}")
            break
        ch = d["choices"][0]; u = d.get("usage",{}) or {}
        log["prompt_tokens"] += u.get("prompt_tokens",0) or 0
        log["completion_tokens"] += u.get("completion_tokens",0) or 0
        log["reasoning_tokens"] += (u.get("completion_tokens_details") or {}).get("reasoning_tokens",0) or 0
        log["cost"] += u.get("cost",0) or 0
        if ch.get("finish_reason") == "length": log["hit_length_cap"] = True
        m = ch["message"]
        msgs.append({k:v for k,v in m.items() if k in ("role","content","tool_calls")})
        tcs = m.get("tool_calls") or []
        if not tcs:
            log["final"] = m.get("content") or ""
            break
        for tc in tcs:
            log["tool_calls"] += 1
            fn = tc["function"]["name"]
            try: args = json.loads(tc["function"]["arguments"] or "{}")
            except Exception: args = {}
            try:
                res = DISPATCH[fn](workdir, **args) if fn in DISPATCH else f"未知工具 {fn}"
            except Exception as e:
                res = f"工具执行异常: {type(e).__name__}: {e}"
            log["trace"].append({"iter":it+1,"tool":fn,
                                 "args":{k:(str(v)[:200]) for k,v in args.items()},
                                 "result_len":len(str(res))})
            msgs.append({"role":"tool","tool_call_id":tc["id"],
                         "name":fn,"content":str(res)[:20000]})
    log["elapsed"] = round(time.time()-t0, 1)
    (workdir/"log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    (workdir/"messages.json").write_text(json.dumps(msgs, ensure_ascii=False, indent=2), encoding="utf-8")
    return log
