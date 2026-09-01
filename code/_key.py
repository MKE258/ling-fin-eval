# key 从环境变量 OPENROUTER_API_KEY 或同目录 .openrouter_key 文件读取
# 实际 key 不包含在本仓库中
"""统一取 key：优先读同目录 .openrouter_key 文件，其次环境变量。key 不打印、不落日志。"""
import os, pathlib

def load():
    f = pathlib.Path(__file__).with_name(".openrouter_key")
    if f.exists():
        k = f.read_text(encoding="utf-8-sig").strip()
        if k:
            return k, "文件 .openrouter_key"
    k = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if k:
        return k, "环境变量"
    raise SystemExit("没找到 key：请在 tests/.openrouter_key 里粘贴，或设置环境变量")
