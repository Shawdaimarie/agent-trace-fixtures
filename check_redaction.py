"""Check a UTF-8 output for the corpus's exact synthetic sensitive markers."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    manifest = json.loads(Path(__file__).with_name('manifest.json').read_text())
    markers = [marker for item in manifest['fixtures'] for marker in item.get('sensitive_markers', [])]
    try:
        with args.output.open('rb') as handle:
            raw = handle.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError
        output = raw.decode('utf-8')
    except (OSError, ValueError):
        print('ERROR: output must be a readable UTF-8 file of at most 1 MiB')
        return 2
    found = sum(marker in output for marker in markers)
    print(f"{'FAIL' if found else 'PASS'}: {found} exact synthetic markers remain")
    return int(bool(found))


if __name__ == '__main__':
    raise SystemExit(main())
