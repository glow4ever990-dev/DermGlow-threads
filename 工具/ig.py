"""把同一篇內容也發到 Instagram（只有帶圖的才發，純文字 IG 不收）

需要 GitHub secret：IG_TOKEN（Instagram 專業帳號的存取權杖）
沒有這個 secret 就整個跳過，不影響 Threads 發布。

IG 的規矩跟 Threads 不一樣：
  只收 JPEG、輪播最多 10 張、文案最多 2200 字、影片要走 REELS
"""
import os, sys, time
import requests

API = "https://graph.instagram.com/v21.0"
CAPTION_MAX = 2200
CAROUSEL_MAX = 10
VID = {".mp4", ".mov"}


def token():
    return os.environ.get("IG_TOKEN", "")


def call(method, path, **params):
    params["access_token"] = token()
    r = requests.request(method, f"{API}/{path}", params=params, timeout=120)
    if not r.ok:
        raise RuntimeError(f"IG API 錯誤 {r.status_code}: {r.text[:300]}")
    return r.json()


def me():
    if not hasattr(me, "v"):
        me.v = call("GET", "me", fields="user_id")["user_id"]
    return me.v


def wait_ready(cid, tries=40):
    for _ in range(tries):
        s = call("GET", cid, fields="status_code,status")
        if s.get("status_code") == "FINISHED":
            return
        if s.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"IG 容器處理失敗: {s}")
        time.sleep(6)
    raise RuntimeError("IG 容器處理超時")


def container(url, caption=None, is_video=False, child=False):
    kw = {"caption": caption} if caption else {}
    if child:
        kw["is_carousel_item"] = "true"
    if is_video:
        kw.update(media_type="REELS", video_url=url)
    else:
        kw["image_url"] = url
    cid = call("POST", f"{me()}/media", **kw)["id"]
    wait_ready(cid)
    return cid


def publish(text, media, url_of):
    """media 是本機檔案清單，url_of(f) 回傳它的公開網址。
    回傳 IG 貼文 id，或 None（這篇不適合發 IG）"""
    if not token():
        return None
    jpgs = [f for f in media if f.suffix.lower() in (".jpg", ".jpeg")]
    vids = [f for f in media if f.suffix.lower() in VID]
    if not jpgs and not vids:
        print("IG：這篇沒有圖或影片，跳過")
        return None
    dropped = len(media) - len(jpgs) - len(vids)
    if dropped:
        print(f"::warning::IG：有 {dropped} 個檔案格式不支援，只送了 JPEG 和影片")

    caption = text[:CAPTION_MAX]
    if len(vids) == 1 and not jpgs:
        cid = container(url_of(vids[0]), caption, is_video=True)
    elif len(jpgs) == 1 and not vids:
        cid = container(url_of(jpgs[0]), caption)
    else:
        items = (jpgs + vids)[:CAROUSEL_MAX]
        if len(items) < len(jpgs) + len(vids):
            print(f"::warning::IG：輪播最多 {CAROUSEL_MAX} 個，只送了前 {CAROUSEL_MAX} 個")
        kids = [container(url_of(f), is_video=f.suffix.lower() in VID, child=True) for f in items]
        cid = call("POST", f"{me()}/media", media_type="CAROUSEL",
                   children=",".join(kids), caption=caption)["id"]
        wait_ready(cid)
    return call("POST", f"{me()}/media_publish", creation_id=cid)["id"]


def try_publish(text, media, url_of):
    """IG 出問題不要拖累 Threads：失敗只印警告"""
    try:
        pid = publish(text, media, url_of)
        if pid:
            print(f"IG 也發了：{pid}")
        return pid
    except Exception as e:
        print(f"::warning::IG 發布失敗（Threads 不受影響）：{e}")
        return None
