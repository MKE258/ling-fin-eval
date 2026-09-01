# -*- coding: utf-8 -*-
"""全量执行：80 轮。结果增量落盘，可中断续跑。"""
import sys, json, pathlib, time
sys.stdout.reconfigure(encoding="utf-8")
import runner, tasks

OUT = pathlib.Path("_runs"); OUT.mkdir(exist_ok=True)
RESULTS = OUT / "results.jsonl"
MODELS = ["inclusionai/ling-3.0-flash-fin:free", "inclusionai/ling-3.0-flash"]
REPEATS = {"F": 48, "A": 42, "C": 42, "D": 30, "H": 24, "B": 16, "E": 12, "G": 12}  # 失败集中的任务优先

done = set()
if RESULTS.exists():
    for line in RESULTS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line); done.add((d["model"], d["task"], d["run"]))

ONLY = sys.argv[1] if len(sys.argv) > 1 else None   # 可选：只跑含该子串的模型
plan = [(m, t, i) for t, n in REPEATS.items() for m in MODELS for i in range(n)
        if (ONLY is None or ONLY in m)]
if ONLY: print(f"仅执行模型包含 '{ONLY}' 的轮次", flush=True)
todo = [x for x in plan if x not in done]
print(f"计划 {len(plan)} 轮，已完成 {len(done)}，本次待跑 {len(todo)}", flush=True)

t_start = time.time()
for k, (model, task, idx) in enumerate(todo, 1):
    cfg = tasks.CONFIG.get(task, {})
    prompt = tasks.build_task_G() if task == "G" else tasks.TASKS[task]
    log = runner.run(model, task, prompt, idx, OUT, **cfg)
    with RESULTS.open("a", encoding="utf-8") as f:
        slim = {x: log[x] for x in ("model","task","run","iters","tool_calls",
                "prompt_tokens","completion_tokens","reasoning_tokens","cost",
                "elapsed","hit_length_cap","http_errors")}
        slim["final_len"] = len(log["final"] or "")
        f.write(json.dumps(slim, ensure_ascii=False) + "\n")
    el = time.time() - t_start
    print(f"[{k}/{len(todo)}] {task} {model.split('/')[-1]:26s} r{idx:<2d} "
          f"iters={log['iters']:<3d} tools={log['tool_calls']:<3d} {log['elapsed']:6.1f}s "
          f"err={len(log['http_errors'])}  累计 {el/60:.1f} 分钟", flush=True)
print(f"\n全部完成，总耗时 {(time.time()-t_start)/60:.1f} 分钟")
