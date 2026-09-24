"""把根目錄裡編號最小的一篇發布到 Threads，發完把檔案移進 posted/

一篇貼文 = 根目錄裡同一個編號的檔案：
  011.txt          文案（可省略）
  011.jpg          圖，多張就 011-2.jpg、011-3.jpg……
  011.mp4          影片也可以
不用建資料夾，編號一樣就是同一篇。

兩步走（由 workflow 依次呼叫）：
  python 工具/post.py          發布編號最小的一篇
  python 工具/post.py record   在最新的倉庫上把那些檔案移進 posted/
"""
import calendar, json, os, random, re, shutil, sys, time
from pathlib import Path
from urllib.parse import quote
import requests
from split import split_text

API = "https://graph.threads.net/v1.0"
REPO = os.environ.get("GITHUB_REPOSITORY", "")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
ROOT, POSTED = Path("."), Path("posted")
LOG = POSTED / "發布記錄.csv"
LAST = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "last_post.json"
IMG_OK = {".jpg", ".jpeg", ".png"}
VID_OK = {".mp4", ".mov"}
NAME = re.compile(r"^(\d+)(?:-(\d+))?$")      # 011 / 011-2


def groups(folder=ROOT):
    """根目錄裡照編號分組：{'011': [011.txt, 011.jpg, 011-2.jpg]}"""
    out = {}
    for f in sorted(folder.iterdir()):
        if not f.is_file() or f.name.startswith("."):
            continue
        m = NAME.match(f.stem)
        if m and f.suffix.lower() in IMG_OK | VID_OK | {".txt"}:
            out.setdefault(m.group(1), []).append(f)
    return dict(sorted(out.items(), key=lambda kv: int(kv[0])))


def is_draft(key, folder=ROOT):
    """還有 草稿NNN.txt 存在，就代表這篇還沒放行"""
    return (folder / f"草稿{key}.txt").exists()


def read_group(files):
    """回傳 (文案, 媒體清單, 問題)"""
    txts = [f for f in files if f.suffix.lower() == ".txt"]
    media = sorted((f for f in files if f.suffix.lower() in IMG_OK | VID_OK),
                   key=lambda f: (len(f.stem), f.stem))
    text = "\n\n".join(t.read_text("utf-8").strip() for t in txts)
    if not text and not media:
        return text, media, "沒有內容"
    if len(media) > 20:
        return text, media, f"{len(media)} 個媒體檔，超過上限 20"
    return text, media, None


def call(method, path, **params):
    params["access_token"] = os.environ["THREADS_TOKEN"]
    r = requests.request(method, f"{API}/{path}", params=params, timeout=60)
    if not r.ok:
        sys.exit(f"API 錯誤 {r.status_code}: {r.text}")
    return r.json()


def me_id():
    if not hasattr(me_id, "v"):
        me_id.v = call("GET", "me", fields="id")["id"]
    return me_id.v


def media_url(p):
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{quote(p.as_posix())}"


def wait_ready(cid, tries=20):
    for _ in range(tries):
        s = call("GET", cid, fields="status,error_message")
        if s.get("status") == "FINISHED":
            return
        if s.get("status") in ("ERROR", "EXPIRED"):
            sys.exit(f"容器處理失敗: {s}")
        time.sleep(6)
    sys.exit("容器處理超時")


def new(**kw):
    cid = call("POST", f"{me_id()}/threads", **kw)["id"]
    wait_ready(cid, 60 if kw.get("media_type") == "VIDEO" else 20)
    return cid


def media_args(f):
    if f.suffix.lower() in VID_OK:
        return {"media_type": "VIDEO", "video_url": media_url(f)}
    return {"media_type": "IMAGE", "image_url": media_url(f)}


TAG = re.compile(r"#([^\s#]{1,50})")


def pull_tag(text):
    """把文案裡的 #標籤 抽出來單獨傳，寫在內文裡 Threads 不一定會認"""
    m = TAG.search(text)
    if not m:
        return text, None
    tag = m.group(1).strip("．。，,、!！?？~～")
    if not tag or "." in tag or "&" in tag:
        return text, None
    return (text[:m.start()] + text[m.end():]).strip(), tag


def create(text, media, tag=None):
    extra = {"topic_tag": tag} if tag else {}
    if not media:
        return new(media_type="TEXT", text=text, **extra)
    if len(media) == 1:
        return new(text=text, **media_args(media[0]), **extra)
    kids = [new(is_carousel_item="true", **media_args(f)) for f in media]
    return new(media_type="CAROUSEL", children=",".join(kids), text=text, **extra)


def should_post_now():
    """自癒式定時：GitHub 跳過幾次也沒關係，下個小時會自動補上
    規則：布里斯本 8-22 點、距上次至少 4.5 小時、今天還沒滿 3 串"""
    now = time.time()
    bne = time.gmtime(now + 10 * 3600)          # 布里斯本固定 UTC+10
    if not 8 <= bne.tm_hour < 22:
        return False, f"布里斯本現在 {bne.tm_hour} 點，不在發布時段"
    if not LOG.exists():
        return True, ""
    rows = [r.split(",") for r in LOG.read_text("utf-8").splitlines()[1:] if r.strip()]
    today = time.strftime("%Y-%m-%d", bne)
    sent, last = 0, 0
    for r in rows:
        t = calendar.timegm(time.strptime(r[0], "%Y-%m-%d %H:%M"))
        last = max(last, t)
        if time.strftime("%Y-%m-%d", time.gmtime(t + 10 * 3600)) == today:
            sent += 1
    if sent >= 3:
        return False, f"今天已經發了 {sent} 串"
    gap = (now - last) / 3600
    if gap < 4.5:
        return False, f"距上次發布才 {gap:.1f} 小時，還不到 4.5 小時"
    return True, ""


def publish():
    if os.environ.get("GATE") == "1":
        ok, why = should_post_now()
        if not ok:
            print(f"這次不發：{why}")
            return
    LAST.unlink(missing_ok=True)
    for key, files in groups().items():
        if is_draft(key):
            print(f"::warning::跳過 {key}：還是草稿（草稿{key}.txt 改名成 {key}.txt 才會發）")
            continue
        text, media, problem = read_group(files)
        if problem:
            print(f"::warning::跳過 {key}：{problem}")
            continue
        text, tag = pull_tag(text)
        parts = split_text(text)
        pid = first = call("POST", f"{me_id()}/threads_publish",
                           creation_id=create(parts[0], media, tag))["id"]
        for extra in parts[1:]:
            time.sleep(random.randint(40, 90))   # 每篇之間停一下，不要像機器連發
            cid = new(media_type="TEXT", text=extra, reply_to_id=pid)
            pid = call("POST", f"{me_id()}/threads_publish", creation_id=cid)["id"]
        LAST.write_text(json.dumps({"key": key, "files": [f.name for f in files],
                                    "threads_id": first}), "utf-8")
        print(f"已發布 {key}: {first}" + (f"（切成 {len(parts)} 篇串成長文）" if len(parts) > 1 else ""))
        return
    print("沒有待發的內容，這次不發")


def record():
    if not LAST.exists():
        return
    last = json.loads(LAST.read_text("utf-8"))
    POSTED.mkdir(exist_ok=True)
    for name in last["files"]:
        src = ROOT / name
        if src.exists():
            dst = POSTED / name
            if dst.exists():
                dst = POSTED / f"{src.stem}-{last['threads_id']}{src.suffix}"
            shutil.move(src, dst)
    new_log = not LOG.exists()
    with LOG.open("a", encoding="utf-8") as f:
        if new_log:
            f.write("發布時間(UTC),編號,threads_id\n")
        f.write(f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime())},{last['key']},{last['threads_id']}\n")


if __name__ == "__main__":
    record() if sys.argv[1:] == ["record"] else publish()
