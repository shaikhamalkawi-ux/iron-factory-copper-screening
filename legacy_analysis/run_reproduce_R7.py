"""Reproduce the supplementary numerical analyses from the repository root.

Run from the package root with Python and the dependencies in README.md.
Existing generated analysis files are replaced; the source workbook is read-only.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,subprocess,sys

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path(__file__).resolve().parents[1]/"source/Iron Factory.xlsx")
    args=parser.parse_args()
    source=args.source.resolve()
    if not source.is_file(): parser.error(f'Missing workbook: {source}')
    expected='1f403f49d399643455cffaad47d4445dee8acfba40ca14b6452283bd9e7e6b8b'
    if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:
        parser.error('Source hash differs from the reported workbook; this reproduction runner does not accept substituted data.')
    root=Path(__file__).resolve().parent
    spec=importlib.util.spec_from_file_location('ordering_audit',root/'writer1_audit'/'verify_original.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.SOURCE=source; module.main()
    for folder,script in [('shortlist_audit','shortlist_audit.py'),('influence_audit','influence_audit.py'),('random_reference','random_reference.py')]:
        subprocess.run([sys.executable,str(root/folder/script),'--source',str(source)],check=True)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
    print('All four numerical audits completed; original workbook unchanged.')

if __name__=='__main__':main()
