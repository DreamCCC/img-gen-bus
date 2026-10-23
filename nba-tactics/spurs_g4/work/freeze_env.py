"""pip-freeze equivalent for a venv without pip: python freeze_env.py out.txt"""
import sys
from importlib.metadata import distributions

pkgs = sorted({(d.metadata["Name"], d.version) for d in distributions() if d.metadata["Name"]}, key=lambda x: x[0].lower())
lines = [f"# python {sys.version.split()[0]}"] + [f"{n}=={v}" for n, v in pkgs]
open(sys.argv[1], "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print(len(pkgs), "packages")
