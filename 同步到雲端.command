#!/bin/zsh
# 雙擊這個圖示，就把 posts 資料夾裡的內容送上雲端
export PATH="$HOME/.local/bin:$PATH"
cd "$(dirname "$0")" || exit 1

echo "==============================="
echo "   同步內容到雲端"
echo "==============================="
echo ""

# 先看看待發的有幾篇
COUNT=$(find posts -mindepth 1 -maxdepth 1 \( -type d -o -name "*.txt" \) 2>/dev/null | wc -l | tr -d ' ')
echo "目前 posts 裡有 $COUNT 篇待發"
echo ""

# 自動整理：HEIC 轉 jpg、簡體轉繁體
python3 tidy.py
echo ""

# 再檢查內容，有 ❌ 就停下來不上傳
if ! python3 check.py; then
  echo ""
  echo "⛔️ 先把上面 ❌ 的問題改好，再雙擊一次同步。"
  echo ""
  echo "（這個視窗可以直接關掉）"
  exit 1
fi
echo ""

git add -A
if git diff --cached --quiet; then
  echo "沒有新東西需要上傳（雲端已經是最新的）"
else
  git -c user.email="glow4ever990-dev@users.noreply.github.com" \
      -c user.name="glow4ever990-dev" \
      commit -q -m "更新內容 $(date '+%Y-%m-%d %H:%M')"
  echo "已打包這次的改動"
fi

echo "正在跟雲端同步……"
if git pull -q --rebase && git push -q; then
  echo ""
  echo "✅ 完成！$COUNT 篇已在雲端排隊"
  echo "   發布時間：每天 9:00 / 12:00 / 15:00 / 18:00 / 21:00（布里斯本）"
else
  echo ""
  echo "❌ 同步失敗。把上面的紅字截圖問 Claude。"
fi

echo ""
echo "（這個視窗可以直接關掉）"
