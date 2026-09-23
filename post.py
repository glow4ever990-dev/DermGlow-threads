"""从 posts/ 里取排最前的一个文件夹发布到 Threads，发完挪进 posted/

每篇帖子 = posts/ 下的一个文件夹，里面放：
  一个 .txt 文件（文案，可省略）+ 若干张 .jpg/.jpeg/.png 图（可省略）
文件夹按名字排序发，建议起名 001、002、003……
1 张图 = 单图帖，2~20 张 = 轮播，没图 = 纯文字。

两步走（由 workflow 依次调用）：
  python post.py          发布排最前的文件夹，把发了哪个记到临时文件
  python post.py record   在最新的仓库上把那个文件夹挪进 posted/ 并记日志
这样即使发帖时你正好在手机上改东西，也不会丢改动或重复发。
"""
import json, os, shutil, sys, time
from pathlib import Path
from urllib.parse import quote
import requests

API = "https://graph.threads.net/v1.0"
REPO = os.environ.get("GITHUB_REPOSITORY", "")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
POSTS, POSTED = Path("posts"), Path("posted")
LOG = POSTED / "发布记录.csv"
LAST = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "last_post.json"
IMG_OK = {".jpg", ".jpeg", ".png"}  # Threads 只收这几种


def me_id():
    if not hasattr(me_id, "v"):
        me_id.v = call("GET", "me", fields="id")["id"]
    return me_id.v


def call(method, path, **params):
    params["access_token"] = os.environ["THREADS_TOKEN"]
    r = requests.request(method, f"{API}/{path}", params=params, timeout=60)
    if not r.ok:
        sys.exit(f"API 错误 {r.status_code}: {r.text}")
    return r.json()


def img_url(p):
    # 仓库里的图 -> GitHub raw 链接（需公开仓库）；中文/空格文件名要转码
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{quote(p.as_posix())}"


def wait_ready(cid):
    for _ in range(20):
        s = call("GET", cid, fields="status,error_message")
        if s.get("status") == "FINISHED":
            return
        if s.get("status") in ("ERROR", "EXPIRED"):
            sys.exit(f"容器处理失败: {s}")
        time.sleep(6)
    sys.exit("容器处理超时")


def new(**kw):
    cid = call("POST", f"{me_id()}/threads", **kw)["id"]
    wait_ready(cid)
    return cid


def read_folder(d):
    """返回 (文案, 图片列表, 问题)；有问题的文件夹跳过不发"""
    files = sorted(f for f in d.iterdir() if f.is_file() and not f.name.startswith("."))
    txts = [f for f in files if f.suffix.lower() == ".txt"]
    imgs = [f for f in files if f.suffix.lower() in IMG_OK]
    bad = [f.name for f in files if f not in txts and f not in imgs]
    text = "\n\n".join(t.read_text("utf-8").strip() for t in txts)
    if bad:
        return text, imgs, f"有不支持的文件（只收 jpg/png）：{', '.join(bad)}"
    if not text and not imgs:
        return text, imgs, "文件夹是空的"
    if len(text) > 500:
        return text, imgs, f"文案 {len(text)} 字，超过 Threads 上限 500 字"
    if len(imgs) > 20:
        return text, imgs, f"{len(imgs)} 张图，超过上限 20 张"
    return text, imgs, None


def create(text, imgs):
    urls = [img_url(i) for i in imgs]
    if not urls:
        return new(media_type="TEXT", text=text)
    if len(urls) == 1:
        return new(media_type="IMAGE", image_url=urls[0], text=text)
    kids = [new(media_type="IMAGE", image_url=u, is_carousel_item="true") for u in urls]
    return new(media_type="CAROUSEL", children=",".join(kids), text=text)


def publish():
    LAST.unlink(missing_ok=True)
    folders = sorted(d for d in POSTS.iterdir() if d.is_dir()) if POSTS.exists() else []
    for d in folders:
        text, imgs, problem = read_folder(d)
        if problem:
            # GitHub 页面上会显示黄色警告，这个文件夹留着等你改
            print(f"::warning::跳过 {d.name}：{problem}")
            continue
        pid = call("POST", f"{me_id()}/threads_publish",
                   creation_id=create(text, imgs))["id"]
        LAST.write_text(json.dumps({"folder": d.name, "threads_id": pid}), "utf-8")
        print(f"已发布 {d.name}: {pid}")
        return
    print("posts 里没有可发的内容，这次不发")


def record():
    if not LAST.exists():
        return
    last = json.loads(LAST.read_text("utf-8"))
    POSTED.mkdir(exist_ok=True)
    src, dst = POSTS / last["folder"], POSTED / last["folder"]
    if dst.exists():  # 名字撞了就加上帖子 id
        dst = POSTED / f"{last['folder']}-{last['threads_id']}"
    if src.exists():
        shutil.move(src, dst)
    new_log = not LOG.exists()
    with LOG.open("a", encoding="utf-8") as f:
        if new_log:
            f.write("发布时间(UTC),文件夹,threads_id\n")
        f.write(f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime())},{last['folder']},{last['threads_id']}\n")


if __name__ == "__main__":
    record() if sys.argv[1:] == ["record"] else publish()
