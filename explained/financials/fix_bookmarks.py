"""Give every bookmark in a .docx its own id (the docx library numbers them all 1, which Word may flag for repair).
Usage: python fix_bookmarks.py file.docx   (rewrites the file in place)"""
import re
import shutil
import sys
import tempfile
import zipfile

path = sys.argv[1]
with zipfile.ZipFile(path) as z:
    items = [(i, z.read(i.filename)) for i in z.infolist()]

counter = 0


def renumber(m):
    global counter
    tag = m.group(0)
    if tag.startswith("<w:bookmarkStart"):
        counter += 1
    return re.sub(r'w:id="\d+"', f'w:id="{counter}"', tag)


tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
    for info, data in items:
        if info.filename == "word/document.xml":
            data = re.sub(r"<w:bookmark(?:Start|End)[^>]*/>", renumber, data.decode("utf8")).encode("utf8")
        if info.filename.endswith("/"):
            continue
        out.writestr(info, data)
shutil.move(tmp, path)
print(f"renumbered {counter} bookmarks")
