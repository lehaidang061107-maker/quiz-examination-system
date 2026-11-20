"""Tạo/cập nhật mục lục (bấm để nhảy tới phần cần đọc) ở đầu các file .md.

Mục lục nằm giữa hai dòng <!-- toc --> và <!-- /toc -->, đặt ngay dưới tiêu đề lớn (#).
Sửa hay thêm tiêu đề ## / ### xong thì chạy lại:

    python scripts/update_toc.py              # cập nhật tất cả file trong FILES
    python scripts/update_toc.py --check      # chỉ báo file nào mục lục đã cũ (không sửa)

Link theo đúng cách GitHub và VS Code tạo anchor cho tiêu đề, nên bấm được ở cả hai nơi.
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = [
    "README.md",
    "docs/huong-dan/1-cai-dat-va-chay.md",
    "docs/huong-dan/2-quy-trinh-lam-task.md",
    "docs/huong-dan/3-viet-code.md",
    "docs/huong-dan/4-kiem-thu.md",
    "docs/quan-ly/ke-hoach.md",
    "docs/quan-ly/yeu-cau-mon-hoc.md",
]
START, END = "<!-- toc -->", "<!-- /toc -->"
HEADING = re.compile(r"^(#{2,3})\s+(.+?)\s*#*\s*$")


def slug(text, seen):
    """Anchor kiểu GitHub: chữ thường, bỏ dấu câu (giữ chữ có dấu tiếng Việt), khoảng trắng -> '-'."""
    text = re.sub(r"`([^`]*)`", r"\1", text).lower()
    kept = "".join(
        c for c in text
        if c in " -_" or unicodedata.category(c)[0] in ("L", "M", "N")
    )
    base = kept.replace(" ", "-")
    count = seen.get(base, 0)
    seen[base] = count + 1
    return base if count == 0 else f"{base}-{count}"


def headings(lines):
    """Các tiêu đề ## và ### ngoài khối code ```."""
    in_code = False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        match = None if in_code else HEADING.match(line)
        if match:
            yield len(match.group(1)), match.group(2)


def build_toc(lines):
    seen, items = {}, []
    for level, title in headings(lines):
        indent = "  " * (level - 2)
        label = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", title)  # bỏ link trong tiêu đề
        items.append(f"{indent}- [{label}](#{slug(title, seen)})")
    return [START, "", "**Mục lục**", "", *items, "", END]


def update(text):
    lines = text.split("\n")
    body = lines
    if START in lines:
        start, end = lines.index(START), lines.index(END)
        body = lines[:start] + lines[end + 1:]
        # bỏ dòng trống thừa do mục lục cũ để lại
        while start < len(body) and start > 0 and body[start] == "" and body[start - 1] == "":
            del body[start]
    toc = build_toc(body)
    title_at = next(i for i, line in enumerate(body) if line.lstrip("\ufeff").startswith("# "))
    return "\n".join(body[: title_at + 1] + [""] + toc + body[title_at + 1:])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="chỉ kiểm tra, không sửa file")
    args = parser.parse_args()
    stale = []
    for name in FILES:
        path = ROOT / name
        old = path.read_text(encoding="utf-8")
        new = update(old)
        if new != old:
            stale.append(name)
            if not args.check:
                path.write_text(new, encoding="utf-8")
    if args.check and stale:
        sys.exit("Mục lục đã cũ, chạy python scripts/update_toc.py: " + ", ".join(stale))
    print(("Cần cập nhật: " if args.check else "Đã cập nhật: ") + (", ".join(stale) or "không có file nào"))


if __name__ == "__main__":
    main()
