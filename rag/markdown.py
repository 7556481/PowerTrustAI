"""Conservative Markdown block splitter; offsets refer to unchanged decoded text.

ATX/setext headings, blank-line paragraphs and fenced code blocks are recognized.
No Markdown rendering, HTML interpretation or front-matter inference is performed.
"""
from dataclasses import dataclass
import re


PARSER_VERSION = "markdown-blocks-v1"


@dataclass(frozen=True)
class MarkdownFragment:
    raw_text: str
    search_text: str
    heading_path: tuple[str, ...]
    start_offset: int
    end_offset: int
    start_line: int
    end_line: int
    heading_levels: tuple[int, ...]


def split_markdown(raw_text: str) -> tuple[MarkdownFragment, ...]:
    # splitlines recognizes other Unicode separators; only CRLF, LF and CR are
    # line boundaries here, matching the documented stored-text convention.
    lines = re.findall(r"[^\r\n]*(?:\r\n|\r|\n|$)", raw_text)
    if lines and lines[-1] == "":
        lines.pop()
    offsets, total = [], 0
    for line in lines:
        offsets.append(total)
        total += len(line)
    headings, output = [], []
    i = 0
    while i < len(lines):
        body = lines[i].rstrip("\r\n")
        if not body.strip():
            i += 1
            continue
        atx = re.match(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?)|[ \t]*)$", body)
        setext = (i + 1 < len(lines) and body.strip()
                  and re.fullmatch(r" {0,3}(?:=+|-+)[ \t]*", lines[i + 1].rstrip("\r\n")))
        if atx or setext:
            level = len(atx[1]) if atx else (1 if lines[i + 1].lstrip().startswith("=") else 2)
            title = re.sub(r"[ \t]+#+[ \t]*$", "", atx[2] or "") if atx else body.strip()
            headings = [(n, t) for n, t in headings if n < level] + [(level, title)]
            i += 1 if atx else 2
            continue
        start = i
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})", body)
        i += 1
        if fence:
            marker = fence[1]
            closing = re.compile(r"^ {0,3}" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}[ \t]*$")
            while i < len(lines):
                closed = closing.fullmatch(lines[i].rstrip("\r\n"))
                i += 1
                if closed:
                    break
        else:
            while i < len(lines) and lines[i].strip():
                next_body = lines[i].rstrip("\r\n")
                if re.match(r"^ {0,3}(?:#{1,6}(?:[ \t]|$)|`{3,}|~{3,})", next_body):
                    break
                # A setext heading begins a new block rather than being swallowed.
                if i + 1 < len(lines) and re.fullmatch(r" {0,3}(?:=+|-+)[ \t]*", lines[i + 1].rstrip("\r\n")):
                    break
                i += 1
        begin, end = offsets[start], offsets[i - 1] + len(lines[i - 1])
        text = raw_text[begin:end]
        path = tuple(t for _, t in headings)
        search = " ".join((" ".join(path) + "\n" + text).casefold().split())
        output.append(MarkdownFragment(text, search, path, begin, end, start + 1, i,
                                       tuple(n for n, _ in headings)))
    return tuple(output)
