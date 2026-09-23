"""同步前自動整理 posts 裡的素材（會改檔案）

做兩件事：
1. 文案裡的簡體字轉成繁體，並換成台灣慣用詞（軟件→軟體、視頻→影片、信息→資訊…）
2. iPhone 的 HEIC 照片轉成 jpg，原檔移到 原檔備份/ 留著

用法：python3 tidy.py
"""
import shutil, subprocess, sys
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
    cc = OpenCC("s2twp")   # 簡體 -> 繁體（台灣正體，含用詞轉換）
    for txt in sorted(ROOT.glob("*.txt")):
        old = txt.read_text("utf-8")
        new = cc.convert(old)
        if new != old:
            txt.write_text(new, "utf-8")
            diff = sum(1 for a, b in zip(old, new) if a != b)
            print(f"✅ {txt.name}：轉成繁體（改了 {diff} 個字）")


def heic_to_jpg():
    heics = [p for p in sorted(ROOT.glob("*"))
             if p.is_file() and p.suffix.lower() in (".heic", ".heif")]
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


def main():
    heic_to_jpg()
    to_traditional()
    return 0


if __name__ == "__main__":
    sys.exit(main())
