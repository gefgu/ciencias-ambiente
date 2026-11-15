"""Copia resultados (json/csv) para report/figures, de onde os .typ os leem."""
import shutil
from .common import OUT, ROOT

def copy_all():
    dst = ROOT / "report" / "figures"
    dst.mkdir(exist_ok=True)
    for pat in ("m2_*.json", "m3_*.json", "m3_*.csv", "m4_*.json", "m4_*.csv"):
        for f in OUT.glob(pat):
            shutil.copy(f, dst / f.name)

if __name__ == "__main__":
    copy_all()
