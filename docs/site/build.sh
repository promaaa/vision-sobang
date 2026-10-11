#!/bin/sh
# Build the website pages into a checkout of the gh-pages branch of promaaa/vision-sobang.
# Usage: docs/site/build.sh SITE_DIR
set -e
W=$(cd "$(dirname "$0")" && pwd)
S=${1:?usage: docs/site/build.sh SITE_DIR}
python3 "$W/bom.py" "$W/../hardware/bom_extinction.csv" "$W/index.src.html" "$S/index.html"
python3 - "$S/index.html" "$W/diagram.txt" <<'PY'
import sys, html
p, d = sys.argv[1:]
s = open(p).read().replace("<pre>\n<!--DIAGRAM-->\n</pre>", "<pre>" + html.escape(open(d).read()) + "</pre>")
assert "<!--" not in s
open(p, "w").write(s)
PY
mkdir -p "$S/concepts"
python3 "$W/concepts.py" "$S/concepts/index.html"
cp "$W/wiki.css" "$S/wiki.css"
echo "built $S/index.html and $S/concepts/index.html"
