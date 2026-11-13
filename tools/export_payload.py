"""Экспорт JS-движка и встраиваемых файлов в один бинарный ресурс для C#-установщика.

Запускается один раз на этапе сборки. Формат: последовательность
[int32 LE length][bytes UTF-8] в фиксированном порядке:

    MARKER, MARKER_VERSION, INJECT_FUNC, ENGINE,
    ANCHOR_FUNC, ANCHOR_HANDLER, ANCHOR_INSERT,
    css, default_json

Python в рантайме не нужен: всё это компилируется внутрь exe.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import asar_patch  # noqa: E402  (модуль без побочных эффектов)

ROOT = os.path.dirname(HERE)
FIELDS = [
    asar_patch.MARKER,
    asar_patch.MARKER_VERSION,
    asar_patch.INJECT_FUNC,
    asar_patch.ENGINE,
    asar_patch.ANCHOR_FUNC,
    asar_patch.ANCHOR_HANDLER,
    asar_patch.ANCHOR_INSERT,
]


def load_text(name):
    with open(os.path.join(ROOT, name), "rb") as f:
        return f.read().decode("utf-8")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "payload.bin")
    fields = [x.encode("utf-8") for x in FIELDS]
    fields.append(load_text("custom-background.css").encode("utf-8"))
    fields.append(load_text("custom-background.json").encode("utf-8"))

    with open(out, "wb") as f:
        for chunk in fields:
            f.write(struct.pack("<i", len(chunk)))
            f.write(chunk)
    print("payload:", out, sum(len(c) for c in fields), "bytes,", len(fields), "fields")
    print("marker version:", asar_patch.MARKER_VERSION)


if __name__ == "__main__":
    main()
