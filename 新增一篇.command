#!/bin/zsh
# 雙擊：把剛丟進來的圖片影片自動編號，再開一個文案視窗
cd "$(dirname "$0")" || exit 1
setopt NULL_GLOB

# 下一個可用的編號（根目錄和 posted 都看過，不會重號）
next_no() {
  local last=$( { ls . posted 2>/dev/null; } | sed -n 's/^0*\([0-9]\{1,\}\).*/\1/p' | sort -n | tail -1 )
  printf "%03d" $(( 10#${last:-0} + 1 ))
}

# 還沒編號的圖片影片（檔名不是純數字的）
STRAY=()
for f in *.jpg *.jpeg *.png *.heic *.mp4 *.mov *.JPG *.JPEG *.PNG *.HEIC *.MP4 *.MOV; do
  [[ "${f:r}" =~ '^[0-9]+(-[0-9]+)?$' ]] || STRAY+=("$f")
done

NO=$(next_no)

if [ ${#STRAY[@]} -gt 0 ]; then
  echo "幫這些檔案編號成第 $NO 篇："
  i=1
  for f in "${STRAY[@]}"; do
    EXT="${f:e:l}"
    if [ $i -eq 1 ]; then NEW="$NO.$EXT"; else NEW="$NO-$i.$EXT"; fi
    mv "$f" "$NEW"
    echo "   $f → $NEW"
    i=$((i + 1))
  done
  TARGET="草稿$NO.txt"
else
  # 有圖沒文案的編號，優先補文案
  TARGET=""
  for f in *.jpg *.jpeg *.png *.mp4 *.mov; do
    KEY="${${f:r}%%-*}"
    [ -e "$KEY.txt" ] || [ -e "草稿$KEY.txt" ] || { TARGET="草稿$KEY.txt"; break; }
  done
  [ -n "$TARGET" ] || TARGET="草稿$NO.txt"
  echo "這一篇是：$TARGET"
fi

[ -e "$TARGET" ] || : > "$TARGET"
open -a TextEdit "$TARGET"

echo ""
echo "==============================="
echo " 接下來："
echo "  1. 在剛打開的視窗裡寫，簡體也沒關係"
echo "  2. Command+S 存檔，關掉視窗"
echo "  3. 這是草稿，不會被發出去"
echo "     要發的時候，把檔名的「草稿」兩個字拿掉即可"
echo "  4. 雙擊「同步到雲端」（自動轉繁體、轉圖檔、檢查）"
echo "==============================="
echo ""
echo "（這個視窗可以直接關掉）"
