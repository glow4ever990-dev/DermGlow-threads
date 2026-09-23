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
import json, os, re, shutil, sys, time
from pathlib import Path
from urllib.parse import quote
import requests

API = "https://graph.threads.net/v1.0"
REPO = os.environ.get("GITHUB_REPOSITORY", "")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
ROOT, POSTED = Path("."), Path("posted")
LOG = POSTED / "發布記錄.csv"
LAST = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "last_post.json"
IMG_OK = {".jpg", ".jpeg", ".png"}
VID_OK = {".mp4", ".mov"}
LIMIT = 500      # Threads 單篇上限
CHUNK = 180      # 長文切段的目標長度：一屏一段
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


def create(text, media):
    if not media:
        return new(media_type="TEXT", text=text)
    if len(media) == 1:
        return new(text=text, **media_args(media[0]))
    kids = [new(is_carousel_item="true", **media_args(f)) for f in media]
    return new(media_type="CAROUSEL", children=",".join(kids), text=text)


def split_text(text, limit=CHUNK):
    """超過 500 字就切成一串，每段約 180 字，小標題不會落單"""
    if len(text) <= LIMIT:
        return [text]
    paras = []
    for para in [x.strip() for x in text.split("\n\n") if x.strip()]:
        while len(para) > LIMIT:
            cut = max((para.rfind(m, 0, LIMIT) for m in "。！？!?"), default=-1)
            cut = cut + 1 if cut > LIMIT // 3 else LIMIT
            paras.append(para[:cut].strip())
            para = para[cut:].lstrip()
        paras.append(para)
    chunks, cur = [], []
    for para in paras:
        if cur and len("\n\n".join(cur + [para])) > limit:
            chunks.append(cur)
            cur = [para]
        else:
            cur.append(para)
    if cur:
        chunks.append(cur)
    for i in range(len(chunks) - 1):
        while len(chunks[i]) > 1 and len(chunks[i][-1]) < 25:
            chunks[i + 1].insert(0, chunks[i].pop())
    return ["\n\n".join(c) for c in chunks if c]


def publish():
    LAST.unlink(missing_ok=True)
    for key, files in groups().items():
        text, media, problem = read_group(files)
        if problem:
            print(f"::warning::跳過 {key}：{problem}")
            continue
        parts = split_text(text)
        pid = first = call("POST", f"{me_id()}/threads_publish",
                           creation_id=create(parts[0], media))["id"]
        for extra in parts[1:]:
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
