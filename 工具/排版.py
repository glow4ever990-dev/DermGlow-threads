"""把密密麻麻的段落拆成一句一行，掃讀起來輕鬆很多

規則：
  ・一段太長就在句號、問號、驚嘆號、波浪號後面換行
  ・原本的空行（段落分隔）保留
  ・「」『』（）裡面的句號不切，避免把引言切爛
  ・已經很短的一行不動

用法：python3 工具/排版.py          （處理根目錄所有待發的 txt）
      python3 工具/排版.py 007.txt   （只處理指定檔案）
"""
import re, sys
from pathlib import Path

LONG = 20          # 一段超過這個長度就拆成一句一行
STOPS = "。！？～!?"
PAIRS = {"「": "」", "『": "』", "（": "）", "(": ")"}


def split_sentences(para):
    """在標點後換行，但不動成對符號裡面的內容"""
    out, buf, depth = [], "", 0
    closers = set(PAIRS.values())
    for ch in para:
        buf += ch
        if ch in PAIRS:
            depth += 1
        elif ch in closers:
            depth = max(0, depth - 1)
        elif ch in STOPS and depth == 0:
            out.append(buf)
            buf = ""
    if buf.strip():
        out.append(buf)
    # 標點後面緊跟著收尾符號的，補回去
    merged = []
    for s in out:
        if merged and s.strip() and s.strip()[0] in closers | {"』", "」"}:
            merged[-1] += s
        else:
            merged.append(s)
    return [s.strip() for s in merged if s.strip()]


def drop_periods(line):
    """行尾的句號拿掉——台灣人在社群上幾乎不打句號，靠換行斷句"""
    line = line.rstrip()
    return line[:-1] if line.endswith("。") else line


def reflow(text):
    blocks = []
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if "\n" in para:                      # 已經是逐行的（清單之類）
            blocks.append("\n".join(drop_periods(l) for l in para.split("\n")))
            continue
        if len(para) <= LONG:
            blocks.append(drop_periods(para))
            continue
        blocks.append("\n".join(drop_periods(l) for l in split_sentences(para)))
    return "\n\n".join(blocks) + "\n"


def main():
    files = [Path(a) for a in sys.argv[1:]] or sorted(
        f for f in Path(".").glob("*.txt") if re.match(r"^\d+$", f.stem))
    for f in files:
        old = f.read_text("utf-8")
        new = reflow(old)
        if new != old:
            f.write_text(new, "utf-8")
            print(f"✅ {f.name}：重新排版")


if __name__ == "__main__":
    main()
