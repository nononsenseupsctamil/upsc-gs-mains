#!/usr/bin/env bash
# Convert HEIC/large scans under answers/ to JPG ≤ ~600 KB (1600 px wide, quality 70).
# Usage: scripts/compress_images.sh [dir]   (default: answers/)
set -euo pipefail
dir="${1:-answers}"
find "$dir" -type f \( -iname '*.heic' -o -iname '*.heif' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) -print0 |
while IFS= read -r -d '' f; do
  ext="${f##*.}"; ext="$(printf '%s' "$ext" | tr '[:upper:]' '[:lower:]')"
  size=$(wc -c <"$f")
  if [[ "$ext" != heic && "$ext" != heif && "$size" -le 600000 ]]; then continue; fi
  out="${f%.*}.jpg"
  if command -v magick >/dev/null; then
    magick "$f" -auto-orient -resize '1600x>' -quality 70 "$out"
  elif command -v sips >/dev/null; then   # macOS built-in
    sips -s format jpeg -s formatOptions 70 --resampleWidth 1600 "$f" --out "$out" >/dev/null
  else
    echo "install ImageMagick (brew install imagemagick)" >&2; exit 1
  fi
  [[ "$out" != "$f" ]] && rm "$f"
  echo "$out  $(( $(wc -c <"$out") / 1000 )) KB"
done
