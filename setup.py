"""One-command setup — run this after cloning."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run(cmd):
    print(f"  $ {cmd}")
    subprocess.run(cmd, shell=True, check=True)

print("\n=== ShadowBuyer setup ===\n")

# 1. Install deps
print("1. Installing dependencies...")
run(f"{sys.executable} -m pip install -q -r requirements.txt")

# 2. Create .env if missing
env_file = ROOT / ".env"
example_file = ROOT / ".env.example"
if not env_file.exists():
    import shutil
    shutil.copy(example_file, env_file)
    print("2. Created .env from .env.example (add your API keys to enable live calls)")
else:
    print("2. .env already exists")

# 3. Smoke test
print("3. Running demo (fixtures mode — no API keys needed)...")
result = subprocess.run(
    [sys.executable, "demo.py"],
    capture_output=True, text=True, cwd=ROOT
)
if result.returncode == 0:
    print("\n   Demo ran successfully.")
    print("   To enable live API calls, add keys to .env (see .env.example)")
else:
    print("\n   Demo output:")
    print(result.stdout[-1000:])
    print(result.stderr[-500:])

print("\nDone. Run:  python demo.py\n")
