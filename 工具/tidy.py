"""同步前自動整理素材（會改檔案）

做兩件事：
1. 文案裡的簡體字轉成繁體，並換成台灣慣用詞（軟件→軟體、視頻→影片、信息→資訊…）
2. HEIC 和 PNG 轉成 jpg（Instagram 只收 JPEG），原檔移到 原檔備份/ 留著

用法：python3 tidy.py
"""
import re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(".")
BACKUP = Path("原檔備份")
MAXPX = 2048          # 長邊超過就縮到這個尺寸，省流量也避開 8MB 上限
QUALITY = "80"


def to_traditional():
    try:
        from opencc import OpenCC
    except ImportError:
        print("⚠️  簡繁轉換工具沒裝，跳過這一步")
        print("   要裝的話執行：python3 -m pip install --user opencc-python-reimplemented")
        return
    cc = OpenCC("s2tw")    # 只換字形，不換詞彙，避免把專業詞改成別的意思
    # 少數台灣慣用詞單獨換，全部是安全、不會改變意思的
    WORDS = {"軟件": "軟體", "視頻": "影片", "信息": "資訊", "默認": "預設",
             "屏幕": "螢幕", "網絡": "網路", "質量": "品質", "數據": "數據"}
    for txt in sorted(ROOT.glob("*.txt")):
        old = txt.read_text("utf-8")
        new = cc.convert(old)
        for a, b in WORDS.items():
            new = new.replace(a, b)
        if new != old:
            txt.write_text(new, "utf-8")
            diff = sum(1 for a, b in zip(old, new) if a != b)
            print(f"✅ {txt.name}：轉成繁體（改了 {diff} 個字）")


def heic_to_jpg():
    heics = [p for p in sorted(ROOT.glob("*"))
             if p.is_file() and p.suffix.lower() in (".heic", ".heif", ".png")]
    if not heics:
        return
    BACKUP.mkdir(exist_ok=True)
    for src in heics:
        dst = src.with_suffix(".jpg")
        if dst.exists():
            dst = src.with_name(src.stem + "-轉檔.jpg")
        r = subprocess.run(
            ["sips", "-s", "format", "jpeg", "-s", "formatOptions", QUALITY,
             "-Z", str(MAXPX), str(src), "--out", str(dst)],
            capture_output=True, text=True)
        if r.returncode != 0 or not dst.exists():
            print(f"❌ {src.name} 轉檔失敗：{r.stderr.strip()[:80]}")
            continue
        shutil.move(src, BACKUP / src.name)
        mb = dst.stat().st_size / 1048576
        print(f"✅ {src.name} → {dst.name}（{mb:.1f}MB，原檔移到 原檔備份/）")


def ig_safe_copies():
    """IG 只收 4:5 到 1.91:1 的圖，超出範圍的補白邊存一份到 IG用/
    （Threads 不挑比例，所以原圖不動）"""
    out = Path("IG用")
    for img in sorted(ROOT.glob("*.jpg")) + sorted(ROOT.glob("*.jpeg")):
        if not re.match(r"^\d+(-\d+)?$", img.stem):
            continue
        r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(img)],
                           capture_output=True, text=True)
        nums = [int(x.split(":")[1]) for x in r.stdout.splitlines() if ":" in x and x.split(":")[1].strip().isdigit()]
        if len(nums) < 2:
            continue
        w, h = nums[0], nums[1]
        ratio = w / h
        if 0.8 <= ratio <= 1.91:
            continue                       # 比例本來就合格
        dst = out / img.name
        if dst.exists() and dst.stat().st_mtime >= img.stat().st_mtime:
            continue
        out.mkdir(exist_ok=True)
        if ratio < 0.8:                    # 太高 -> 左右補白到 4:5
            W, H = max(w, int(h * 0.8)), h
        else:                              # 太寬 -> 上下補白到 1.91:1
            W, H = w, max(h, int(w / 1.91))
        subprocess.run(["sips", "-p", str(H), str(W), "--padColor", "FFFFFF",
                        str(img), "--out", str(dst)], capture_output=True)
        print(f"✅ {img.name}：比例 {ratio:.2f} 不合 IG，補白邊存到 IG用/")


def main():
    heic_to_jpg()
    to_traditional()
    ig_safe_copies()
    return 0


if __name__ == "__main__":
    sys.exit(main())
