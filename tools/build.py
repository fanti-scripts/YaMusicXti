"""Сборка самодостаточного установщика: csc.exe + встроенный payload.

Python нужен только здесь, на этапе сборки. В самом exe его нет.
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "installer", "src")
PAYLOAD = os.path.join(ROOT, "installer", "payload.bin")
MANIFEST = os.path.join(SRC, "app.manifest")
OUT = os.path.join(ROOT, "Фон Яндекс Музыки.exe")

CSC_CANDIDATES = [
    r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
    r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe",
]


def main():
    csc = next((p for p in CSC_CANDIDATES if os.path.exists(p)), None)
    if not csc:
        sys.exit("csc.exe не найден (.NET Framework 4.x)")

    print("payload…")
    subprocess.check_call([sys.executable, os.path.join(ROOT, "tools", "export_payload.py"), PAYLOAD])

    sources = sorted(glob.glob(os.path.join(SRC, "*.cs")))
    if not sources:
        sys.exit("нет исходников в " + SRC)

    if os.path.exists(OUT):
        os.remove(OUT)

    cmd = [
        csc,
        "/nologo",
        "/target:winexe",
        "/platform:anycpu",
        "/optimize+",
        "/debug-",
        "/codepage:65001",
        "/win32manifest:" + MANIFEST,
        "/resource:" + PAYLOAD + ",payload.bin",
        "/out:" + OUT,
    ] + sources

    print("csc…")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)
    if not os.path.exists(OUT):
        sys.exit("exe не появился: " + OUT)
    print("готово:", OUT)
    print("размер: %.1f КБ" % (os.path.getsize(OUT) / 1024.0))


if __name__ == "__main__":
    main()
