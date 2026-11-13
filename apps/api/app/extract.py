"""Turn an uploaded file into text, in memory. Nothing is written to disk and nothing here logs content.

Supported: plain text (.txt .md .log .xml ...), .csv / .json (returned unchanged so the structure survives),
.docx (python-docx), .eml (body + attachment NAMES), .msg (body + attachment names), text-layer .pdf (pypdf).
Attachment CONTENT is never read unless the caller passes include_attachments=True (explicit user consent).
"""
from __future__ import annotations
import io, os
from email import policy
from email.parser import BytesParser

class Unsupported(Exception):
    pass

TEXT_EXT = {".txt", ".md", ".log", ".xml", ".csv", ".tsv", ".json", ".jsonl", ".yaml", ".yml", ".html", ".htm", ".fix", ".swift", ".edi", ".mt940", ".sta"}

def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try: return data.decode(enc)
        except (UnicodeDecodeError, UnicodeError): continue
    return data.decode("latin-1")

def _docx(data: bytes) -> str:
    import docx
    d = docx.Document(io.BytesIO(data)); out = []
    for sec in d.sections:
        for p in sec.header.paragraphs:
            if p.text.strip(): out.append(p.text)
    body = d.element.body
    for child in body.iterchildren():           # paragraphs and tables in document order
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            out.append("".join(t.text or "" for t in child.iter() if t.tag.endswith("}t")))
        elif tag == "tbl":
            for row in child.iter():
                if row.tag.endswith("}tr"):
                    cells = ["".join(t.text or "" for t in c.iter() if t.tag.endswith("}t")) for c in row if c.tag.endswith("}tc")]
                    out.append("\t".join(cells))
    for sec in d.sections:
        for p in sec.footer.paragraphs:
            if p.text.strip(): out.append(p.text)
    return "\n".join(out)

def _eml(data: bytes, include_attachments: bool) -> tuple[str, list[str]]:
    msg = BytesParser(policy=policy.default).parsebytes(data)
    head = [f"{h}: {msg[h]}" for h in ("From", "To", "Cc", "Date", "Subject") if msg[h]]
    body = msg.get_body(preferencelist=("plain", "html"))
    text = body.get_content() if body is not None else ""
    if body is not None and body.get_content_type() == "text/html": text = _strip_html(text)
    names, extra = [], []
    for part in msg.iter_attachments():
        name = part.get_filename() or "(unnamed attachment)"; names.append(name)
        if include_attachments:
            try:
                t, _ = extract(name, part.get_payload(decode=True) or b"", False)
                extra.append(f"\n--- attachment: {name} ---\n{t}")
            except Unsupported:
                extra.append(f"\n--- attachment: {name} (format not supported; not included) ---")
    out = "\n".join(head) + "\n\n" + text.strip() + "\n"
    if names: out += "\nAttachments: " + ", ".join(names) + "\n"
    return out + "".join(extra), names

def _strip_html(html: str) -> str:
    from html.parser import HTMLParser
    class P(HTMLParser):
        def __init__(self): super().__init__(); self.out = []; self.skip = 0
        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"): self.skip += 1
            if tag in ("br", "p", "div", "tr", "li"): self.out.append("\n")
        def handle_endtag(self, tag):
            if tag in ("script", "style") and self.skip: self.skip -= 1
        def handle_data(self, d):
            if not self.skip: self.out.append(d)
    p = P(); p.feed(html)
    return "".join(p.out)

def _msg(data: bytes) -> tuple[str, list[str]]:
    """Outlook .msg via olefile (BSD): subject, sender, recipients, plain body, attachment names. No attachment content."""
    import olefile
    ole = olefile.OleFileIO(io.BytesIO(data))
    def prop(path, code):
        for suffix, dec in (("001F", "utf-16-le"), ("001E", "cp1252")):
            p = path + [f"__substg1.0_{code}{suffix}"]
            if ole.exists(p): return ole.openstream(p).read().decode(dec, "replace").rstrip("\x00")
        return ""
    head = [f"{k}: {v}" for k, v in (("From", prop([], "0C1A")), ("To", prop([], "0E04")), ("Cc", prop([], "0E03")), ("Subject", prop([], "0037"))) if v]
    names = []
    for entry in ole.listdir(streams=False, storages=True):
        if len(entry) == 1 and entry[0].startswith("__attach_version1.0_"):
            names.append(prop(entry, "3707") or prop(entry, "3704") or "(unnamed attachment)")
    out = "\n".join(head) + "\n\n" + prop([], "1000").strip() + "\n"
    if names: out += "\nAttachments: " + ", ".join(names) + "\n"
    return out, names

def _pdf(data: bytes) -> str:
    from pypdf import PdfReader
    r = PdfReader(io.BytesIO(data))
    if r.is_encrypted: raise Unsupported("password-protected PDFs are not supported")
    text = "\n\n".join((p.extract_text() or "") for p in r.pages)
    if not text.strip(): raise Unsupported("this PDF has no text layer (scanned image); OCR is not supported")
    return text

def extract(filename: str, data: bytes, include_attachments: bool = False) -> tuple[str, dict]:
    """-> (text, meta). meta holds only non-content facts: format, attachment count, characters."""
    ext = os.path.splitext(filename.lower())[1]; names: list[str] = []
    try:
        if ext == ".docx" or data[:4] == b"PK\x03\x04" and ext not in TEXT_EXT: text, fmt = _docx(data), "docx"
        elif ext == ".pdf" or data[:5] == b"%PDF-": text, fmt = _pdf(data), "pdf"
        elif ext == ".eml": (text, names), fmt = _eml(data, include_attachments), "eml"
        elif ext == ".msg" or data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1": (text, names), fmt = _msg(data), "msg"
        elif ext in TEXT_EXT or ext == "": text, fmt = _decode(data), (ext[1:] or "txt")
        else: raise Unsupported(f"unsupported file type {ext}")
    except Unsupported:
        raise
    except Exception as e:  # noqa: BLE001  parser errors can quote file content: report the type only
        raise Unsupported(f"could not read this {ext or 'file'} ({type(e).__name__})") from None
    return text, {"format": fmt, "attachments": len(names), "attachments_included": bool(include_attachments and names), "chars": len(text)}
