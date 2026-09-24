// Đọc văn bản đã render của một trang qua Chrome DevTools Protocol.
// Dùng cho những trang cần JavaScript mới hiện nội dung (luật Kaggle, leaderboard).
//
//   node scripts/rules_text.js <url> <out.txt>
//
// Chrome chạy headless với một user-data-dir MỚI tạo cho riêng lần chạy này, nên
// không đụng tới trình duyệt của Plone; profile đó bị xóa khi xong. Chỉ PID do
// chính script này khởi chạy mới bị dừng — không bao giờ dừng theo tên tiến trình.
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const URL = process.argv[2];
const OUT = process.argv[3];
const PORT = 9333;
const CHROME = process.env.CHROME || "google-chrome";
const UD = fs.mkdtempSync(path.join(os.tmpdir(), "rules-text-"));

const chrome = spawn(CHROME, [
  "--headless=new", "--disable-gpu", `--user-data-dir=${UD}`,
  `--remote-debugging-port=${PORT}`, "about:blank",
], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  try {
    let target;
    for (let i = 0; i < 40 && !target; i++) {
      await sleep(500);
      try {
        const list = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
        target = list.find((t) => t.type === "page");
      } catch {}
    }
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((r) => ws.addEventListener("open", r));
    let id = 0;
    const pending = new Map();
    ws.addEventListener("message", (e) => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
    });
    const send = (method, params = {}) => new Promise((r) => {
      const n = ++id; pending.set(n, r); ws.send(JSON.stringify({ id: n, method, params }));
    });
    await send("Page.enable");
    await send("Page.navigate", { url: URL });
    await sleep(20000);
    const res = await send("Runtime.evaluate", { expression: "document.body.innerText", returnByValue: true });
    fs.writeFileSync(OUT, res.result.result.value || "", "utf8");
    console.log("chars", (res.result.result.value || "").length);
    ws.close();
  } catch (e) {
    console.error("failed:", e.message);
  } finally {
    try { process.kill(chrome.pid); } catch {}
    await sleep(1000);
    fs.rmSync(UD, { recursive: true, force: true });
  }
})();
