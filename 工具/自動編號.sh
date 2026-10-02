#!/bin/zsh
# 丟進資料夾的圖片影片自動編號（由背景服務在檔案變動時呼叫）
cd "$(dirname "$0")/.." || exit 1
setopt NULL_GLOB

# 等檔案複製完：連續兩次檢查大小沒變才動手
sleep 8
sizes_now() { for f in *.jpg *.jpeg *.png *.heic *.mp4 *.mov *.JPG *.JPEG *.PNG *.HEIC *.MP4 *.MOV; do
  [[ "${f:r}" =~ '^[0-9]+(-[0-9]+)?$' ]] || stat -f "%z" "$f" 2>/dev/null; done }
A=$(sizes_now); sleep 5; B=$(sizes_now)
[ "$A" = "$B" ] || exit 0          # 還在寫入，下次變動再處理

STRAY=()
for f in *.jpg *.jpeg *.png *.heic *.mp4 *.mov *.JPG *.JPEG *.PNG *.HEIC *.MP4 *.MOV; do
  [[ "${f:r}" =~ '^[0-9]+(-[0-9]+)?$' ]] || STRAY+=("$f")
done
[ ${#STRAY[@]} -eq 0 ] && exit 0

LAST=$( { ls . posted 2>/dev/null; } | sed -n 's/^0*\([0-9]\{1,\}\).*/\1/p' | sort -n | tail -1 )
NO=$(printf "%03d" $(( 10#${LAST:-0} + 1 )))

i=1
for f in "${STRAY[@]}"; do
  EXT="${f:e:l}"
  if [ $i -eq 1 ]; then NEW="$NO.$EXT"; else NEW="$NO-$i.$EXT"; fi
  mv -n "$f" "$NEW" && echo "$(date '+%m-%d %H:%M')  $f → $NEW" >> 工具/編號紀錄.txt
  i=$((i + 1))
done

# 順手開一個草稿檔，等著寫文案（草稿不會被發出去）
[ -e "$NO.txt" ] || [ -e "草稿$NO.txt" ] || : > "草稿$NO.txt"

osascript -e "display notification \"${#STRAY[@]} 個檔案已編號成第 $NO 篇\" with title \"Threads 素材\"" 2>/dev/null
