#!/usr/bin/env python3
"""Portable November 2026 numerical and optional four-figure replay.

Run from any working directory: python nov2026_revision/reproduce_nov2026.py --output PATH [--figures]
All inputs are the public sanitized dataset or public-safe replay ZIPs.
"""
from pathlib import Path
from zipfile import ZipFile
from tempfile import TemporaryDirectory
import argparse,subprocess,sys,hashlib,shutil,json,os
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
EXPECTED='1f403f49d399643455cffaad47d4445dee8acfba40ca14b6452283bd9e7e6b8b'
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
def run(cmd,cwd=None):
    print('RUN', ' '.join(map(str,cmd)),flush=True)
    subprocess.run([str(x) for x in cmd],cwd=cwd,check=True)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',default='reproduced-nov2026')
    p.add_argument('--figures',action='store_true',help='run pixel-parity verification for four figures (Bash and artifact_tool required)')
    args=p.parse_args()
    out=Path(args.output).resolve()
    assert not out.exists() or not any(out.iterdir()),'Choose an empty output directory to avoid overwriting outputs'
    out.mkdir(parents=True,exist_ok=True)
    source=REPO/'source'/'Iron Factory.xlsx'
    assert source.exists(),f'Missing source {source}'
    assert sha(source)==EXPECTED,'Source SHA256 does not match admitted public source'
    with TemporaryDirectory(prefix='iron-v62-replay-') as tmp:
        work=Path(tmp)
        with ZipFile(ROOT/'Iron_Nov2026_S2_Numerical_Replay.zip') as z:
            assert z.testzip() is None
            z.extractall(work/'s2')
        s2=work/'s2'/'04_Supplementary_Data_and_Figures'
        assert sha(s2/'Iron_Factory_public_sanitized.xlsx')==EXPECTED
        assert (s2/'Iron_Factory_public_sanitized.xlsx').read_bytes()==source.read_bytes()
        run([sys.executable,s2/'Baseline_Reproduction_V39'/'run_reproduction.py','--output',out/'numeric_reproduced'])
        run([sys.executable,s2/'verify_mass_arithmetic.py',s2/'Iron_Factory_public_sanitized.xlsx'])
        run([sys.executable,s2/'audit_ms2b_conditional.py'])
        run([sys.executable,s2/'verify_v43_delivery.py'])
        (out/'MS2B_Conditional_Conversion_QA.json').write_bytes((s2/'MS2B_Conditional_Conversion_QA.json').read_bytes())
        if args.figures:
            with ZipFile(ROOT/'Iron_Nov2026_Four_Figure_Source_Replay.zip') as z:
                assert z.testzip() is None
                z.extractall(work/'fig')
            assert sha(work/'fig'/'inputs'/'Iron_Factory_public_sanitized.xlsx')==EXPECTED
            run(['bash','run_all.sh'],cwd=work/'fig')
            shutil.copytree(work/'fig'/'output',out/'figures')
    record={'source_sha256':EXPECTED,'source_unchanged':sha(source)==EXPECTED,'numeric_replay':'PASS','four_figures_pixel_parity':'PASS' if args.figures else 'NOT_RUN_OPTIONAL', 'output':str(out)}
    (out/'EXECUTION_RESULT.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))
if __name__=='__main__': main()
