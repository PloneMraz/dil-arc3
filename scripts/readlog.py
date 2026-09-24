"""Đọc log kernel của Kaggle: nó là một mảng JSON các bản ghi {stream_name, time, data}."""
import json
import sys

path = sys.argv[1]
raw = open(path, encoding="utf-8", errors="replace").read()

try:
    records = json.loads(raw)
except json.JSONDecodeError:
    # Log bị cắt giữa chừng: vá dấu đóng mảng rồi thử lại.
    records = json.loads(raw.rstrip().rstrip(",") + "]")

noise = ("Requirement already satisfied", "Debugger warning", "frozen modules",
         "Debugging will proceed", "Processing /kaggle/input")
lines = []
for r in records:
    s = str(r.get("data", "")).rstrip()
    if s and not any(n in s for n in noise):
        lines.append(s)

print(f"--- {len(records)} ban ghi, {len(lines)} dong co nghia ---")
n = int(sys.argv[2]) if len(sys.argv) > 2 else 35
for s in lines[-n:]:
    print(s)
