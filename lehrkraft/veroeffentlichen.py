"""Baut die Web-Version mit dem Lernpfad-Baukasten und legt sie nach docs/ – das ist die veröffentlichte Fassung.

    python3 lehrkraft/veroeffentlichen.py <pfad-zum-baukasten>

docs/ wird von GitHub Pages ausgeliefert und kann 1:1 auf einen Webserver (Plesk) hochgeladen werden.
Die Seite „Für Lehrkräfte“ und die Musterlösung bleiben draußen.
"""
import shutil
import subprocess
import sys
from pathlib import Path

KURS = Path(__file__).resolve().parent.parent
OHNE = ["lehrkraefte.html", "material/musterloesung-basistext.docx"]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    baukasten = Path(sys.argv[1]).resolve()
    subprocess.run([sys.executable, str(baukasten / "skripte" / "bauen.py"), str(KURS)], check=True)
    ziel = KURS / "docs"
    if ziel.exists():
        shutil.rmtree(ziel)
    shutil.copytree(KURS / "ausgabe" / "web", ziel)
    for datei in OHNE:
        (ziel / datei).unlink(missing_ok=True)
    print(f"✓ Veröffentlichte Fassung in {ziel} – jetzt committen und pushen.")


if __name__ == "__main__":
    main()
