"""把文案切成一串短貼文：第一篇是短鉤子，後面一段一段接下去"""

LIMIT = 500     # Threads 單篇硬上限
HEAD = 40       # 第一篇最多幾個字（動態牆上只看得到前兩行）
CHUNK = 180     # 後面每一篇的目標長度
STOPS = "。！？～!?…"          # 優先在這些字後面切
SOFT = "，、,；;：:"            # 沒有句號才退而求其次


def cut_head(text, limit=HEAD):
    """切出開頭的鉤子，儘量在標點處斷開"""
    if len(text) <= limit:
        return text, ""
    window = text[:limit + 1]
    for marks in (STOPS, SOFT):
        pos = max(window.rfind(m) for m in marks)
        if pos >= limit // 3:
            return text[:pos + 1].strip(), text[pos + 1:].strip()
    return text[:limit].strip(), text[limit:].strip()


def split_text(text):
    text = text.strip()
    if len(text) <= HEAD:
        return [text]

    # 第一篇：短鉤子。先拿第一段，太長就在標點處切開
    first_para, _, rest = text.partition("\n\n")
    head, leftover = cut_head(first_para)
    rest = "\n\n".join(x for x in (leftover, rest) if x.strip())
    if not rest:
        return [head]

    # 其餘照段落打包，每篇約 CHUNK 字
    paras = []
    for para in [x.strip() for x in rest.split("\n\n") if x.strip()]:
        while len(para) > LIMIT:
            cut, para = cut_head(para, LIMIT)
            paras.append(cut)
        paras.append(para)

    chunks, cur = [], []
    for para in paras:
        if cur and len("\n\n".join(cur + [para])) > CHUNK:
            chunks.append(cur)
            cur = [para]
        else:
            cur.append(para)
    if cur:
        chunks.append(cur)

    # 小標題之類的短句，不要落在某一篇的結尾
    for i in range(len(chunks) - 1):
        while len(chunks[i]) > 1 and len(chunks[i][-1]) < 25:
            chunks[i + 1].insert(0, chunks[i].pop())

    return [head] + ["\n\n".join(c) for c in chunks if c]
