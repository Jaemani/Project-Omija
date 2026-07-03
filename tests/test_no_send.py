"""Guardrail smoke (e): the codebase has NO send capability.

CLAUDE.md — 통보는 초안 "생성"까지, 자동 발송·실제 통지 없음. This test asserts
that no SMTP / mail-send API is imported or defined anywhere in the product
source (actions/adapter/store/scripts/registry). Comments that merely state the
absence of a send path ("no send capability") are intentionally NOT matched.
"""

import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC_DIRS = ["actions", "adapter", "store", "scripts", "registry"]

# Deliberately specific: real send/transport surfaces, not the English word
# "send" appearing in a guardrail comment.
_FORBIDDEN = [
    r"\bsmtplib\b",
    r"\bsmtp\b",
    r"\bsendmail\b",
    r"send_email",
    r"send_mail",
    r"\.send\(",
    r"\bdef\s+send\b",
    r"\byagmail\b",
    r"\bsendgrid\b",
]


def _py_files():
    for d in _SRC_DIRS:
        for dirpath, _dirs, files in os.walk(os.path.join(_ROOT, d)):
            if "__pycache__" in dirpath:
                continue
            for f in files:
                if f.endswith(".py"):
                    yield os.path.join(dirpath, f)


def test_no_send_capability_in_source():
    hits = []
    for path in _py_files():
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        for pat in _FORBIDDEN:
            if re.search(pat, text, re.IGNORECASE):
                hits.append((os.path.relpath(path, _ROOT), pat))
    assert hits == [], f"send/smtp capability found in source: {hits}"
