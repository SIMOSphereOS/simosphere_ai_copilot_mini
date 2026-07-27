#!/usr/bin/env python3
"""RST -> Markdown-Konverter fuer die Nextcloud-Doku (RAG-Ingest, Copilot Mini).

Kein Sphinx/docutils noetig — ein fokussierter, zeilenbasierter Konverter fuer genau die
Konstrukte, die in der NC-Doku vorkommen. Ziel ist sauberer Fliesstext + Code fuer die
Vektorsuche, NICHT pixelgenaues Rendering. Bilder/Navigation fliegen raus, Code und Hinweise
bleiben, Cross-Reference-Rollen werden auf ihren sichtbaren Text reduziert.

Je Datei wird die Quell-URL auf docs.nextcloud.com als erste Zeile (H1-Kommentar) mitgeschrieben,
damit der spaetere Index eine CC-BY-Attribution + Zitat-Link tragen kann.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SRC = Path.home() / "nextcloud-docs-src"
OUT = Path.home() / "nextcloud-docs-build" / "md"
MANUALS = ("admin_manual", "user_manual", "developer_manual")
DOCS_BASE = "https://docs.nextcloud.com/server/33"

# Direktiven, deren eingerueckter Block KOMPLETT entfaellt (Navigation, Bilder, Rohausgabe).
_DROP_BLOCK = {
    "toctree",
    "figure",
    "image",
    "raw",
    "mermaid",
    "sectionauthor",
    "contents",
    "index",
}
# Direktiven, deren Inhalt als Codeblock erhalten bleibt.
_CODE_BLOCK = {"code-block", "code", "parsed-literal", "literalinclude"}
# Admonitions: Inhalt bleibt, mit vorangestelltem Label.
_ADMON = {
    "note",
    "warning",
    "tip",
    "important",
    "caution",
    "seealso",
    "attention",
    "hint",
    "danger",
}
# Versionshinweise: auf eine knappe Zeile reduziert.
_VERSION = {"versionadded", "versionchanged", "deprecated"}

# Inline-Rollen ``:role:`text``` bzw. ``:role:`text <target>``` -> nur der sichtbare Text.
_ROLE = re.compile(r":[a-zA-Z][\w+-]*:`([^`]*)`")
# Anonyme/normale Referenzen ``text <target>`` innerhalb der Rolle: nur ``text``.
_ROLE_TARGET = re.compile(r"^(.*?)\s*<[^>]+>$")
# ``inline literal`` -> `inline literal` (Markdown-Code). Doppelte Backticks zuerst.
_LITERAL = re.compile(r"``([^`]+)``")
# RST-Hyperlink ``text <url>``_ -> Text (externe http-URL in Klammern behalten, interne verwerfen).
_HYPERLINK = re.compile(r"`([^`<]+?)\s*<([^>]+)>`__?")
# Einfacher Referenz-Verweis ``text``_ -> Text.
_SIMPLE_REF = re.compile(r"`([^`]+?)`__?")
# Substitutionen |name| entfernen.
_SUBST = re.compile(r"\|[^|]+\|")
# Fuehrender RST-Line-Block-Marker ``| `` am Zeilenanfang.
_LINEBLOCK = re.compile(r"^\s*\|\s?")


def _clean_inline(text: str) -> str:
    def _role_repl(m: re.Match) -> str:
        inner = m.group(1)
        t = _ROLE_TARGET.match(inner)
        return (t.group(1) if t else inner).strip()

    def _link_repl(m: re.Match) -> str:
        label, url = m.group(1).strip(), m.group(2).strip()
        return f"{label} ({url})" if url.startswith(("http://", "https://")) else label

    text = _LINEBLOCK.sub("", text)
    text = _ROLE.sub(_role_repl, text)
    text = _LITERAL.sub(r"`\1`", text)
    text = _HYPERLINK.sub(_link_repl, text)
    text = _SIMPLE_REF.sub(r"\1", text)
    text = _SUBST.sub("", text)
    text = text.replace("\\", "")  # RST-Escapes entschaerfen
    return text


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def convert(text: str) -> str:
    lines = text.replace("\t", "    ").split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Field-Lists / Kommentar-Marker am Zeilenanfang (`:orphan:`, `.. _label:`) ueberspringen.
        if re.match(r"^:[\w-]+:\s", line) or re.match(r"^:[\w-]+:\s*$", line):
            i += 1
            continue

        # Direktive `.. name:: args`
        m = re.match(r"^(\s*)\.\.\s+([a-zA-Z][\w-]*)::(.*)$", line)
        if m:
            base_indent = len(m.group(1))
            name = m.group(2).lower()
            arg = m.group(3).strip()
            # Block einsammeln: Folgezeilen, die tiefer eingerueckt oder leer sind.
            j = i + 1
            block: list[str] = []
            while j < n:
                if lines[j].strip() == "":
                    block.append("")
                    j += 1
                    continue
                if _indent(lines[j]) > base_indent:
                    block.append(lines[j])
                    j += 1
                else:
                    break
            # Fuehrende/abschliessende Leerzeilen im Block trimmen.
            while block and block[0] == "":
                block.pop(0)
            while block and block[-1] == "":
                block.pop()

            if name in _DROP_BLOCK:
                pass  # komplett verwerfen
            elif name in _CODE_BLOCK:
                body = _dedent(block)
                if any(x.strip() for x in body):
                    out.append("```")
                    out.extend(body)
                    out.append("```")
            elif name in _ADMON:
                label = name.capitalize()
                body = [_clean_inline(b) for b in _dedent(block)]
                joined = " ".join(x.strip() for x in body if x.strip())
                if joined:
                    out.append(f"**{label}:** {joined}")
            elif name in _VERSION:
                note = f"(Nextcloud {arg})" if arg else f"({name})"
                out.append(note)
            elif name == "list-table":
                for b in _dedent(block):
                    bs = b.strip()
                    if bs.startswith("* -") or bs.startswith("-"):
                        cell = _clean_inline(bs.lstrip("*- ").strip())
                        if cell:
                            out.append(cell)
            else:
                # Unbekannte Direktive: Inhalt als Text behalten (nichts verlieren).
                for b in _dedent(block):
                    cb = _clean_inline(b.strip())
                    if cb:
                        out.append(cb)
            i = j
            continue

        # Kommentarzeile `.. something` ohne `::`
        if re.match(r"^\s*\.\.(\s|$)", line):
            i += 1
            continue

        # Section-Titel: aktuelle Zeile + Underline aus Wiederholungszeichen.
        if (
            i + 1 < n
            and re.match(r"^[=\-~^\"'`#*+.]{3,}\s*$", lines[i + 1])
            and stripped
        ):
            underline = lines[i + 1].strip()[0]
            level = {"=": "#", "-": "##", "~": "###", "^": "####"}.get(underline, "##")
            out.append(f"{level} {_clean_inline(stripped)}")
            i += 2
            continue
        # Overline+Titel+Underline (dreizeilig)
        if (
            re.match(r"^[=\-~^]{3,}\s*$", line)
            and i + 2 < n
            and lines[i + 1].strip()
            and re.match(r"^[=\-~^]{3,}\s*$", lines[i + 2])
        ):
            out.append(f"# {_clean_inline(lines[i + 1].strip())}")
            i += 3
            continue

        out.append(_clean_inline(line.rstrip()))
        i += 1

    # Mehrfach-Leerzeilen zusammenfassen.
    result: list[str] = []
    blank = False
    for ln in out:
        if ln.strip() == "":
            if not blank:
                result.append("")
            blank = True
        else:
            result.append(ln)
            blank = False
    return "\n".join(result).strip() + "\n"


def _dedent(block: list[str]) -> list[str]:
    indents = [_indent(b) for b in block if b.strip()]
    if not indents:
        return []
    cut = min(indents)
    return [b[cut:] if len(b) >= cut else b for b in block]


def main() -> int:
    total = 0
    for manual in MANUALS:
        for rst in sorted((SRC / manual).rglob("*.rst")):
            rel = rst.relative_to(SRC)
            url = f"{DOCS_BASE}/{rel.with_suffix('.html').as_posix()}"
            try:
                raw = rst.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                raw = rst.read_text(encoding="latin-1")
            body = convert(raw)
            if len(body.strip()) < 40:
                continue  # zu wenig Inhalt (reine Weiterleitungs-/Stub-Seite)
            dest = OUT / rel.with_suffix(".md")
            dest.parent.mkdir(parents=True, exist_ok=True)
            header = f"<!-- source: {url} | Nextcloud Documentation, CC BY 3.0 -->\n"
            dest.write_text(header + body, encoding="utf-8")
            total += 1
    print(f"Konvertiert: {total} Dateien -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
