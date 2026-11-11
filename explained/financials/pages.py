"""Find the page each heading lands on in the rendered PDF (skipping the title and contents pages)."""
import json, subprocess, sys, re
pdf, toc_json, out = sys.argv[1:4]
entries = json.load(open(toc_json))
n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
texts = [subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), "-layout", pdf, "-"], capture_output=True, text=True).stdout
         for i in range(1, n + 1)]
norm = lambda s: re.sub(r"\s+", " ", s)
start = next(i for i, tx in enumerate(texts) if "Contents" in tx) + 1
while start < n and "........" in texts[start]:   # contents may run over two pages
    start += 1
pages = {}
for e in entries:
    key = norm(f"{e['num']} {e['text']}")
    for i in range(start, n):
        if key in norm(texts[i]):
            pages[e["id"]] = i + 1
            break
    else:
        print("NOT FOUND", key)
json.dump(pages, open(out, "w"))
print(n, "pages;", pages)
