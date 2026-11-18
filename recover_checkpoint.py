"""Recover only an incomplete final JSONL write; preserve the original file."""
import argparse
import json
from pathlib import Path
import shutil


def recover(source,output):
    if output.exists():raise ValueError('Recovery destination must be new')
    lines=source.read_bytes().splitlines(keepends=True);valid=[]
    for i,line in enumerate(lines):
        try:json.loads(line)
        except (json.JSONDecodeError,UnicodeDecodeError):
            if i!=len(lines)-1 or line.endswith(b'\n'):raise ValueError('Not an incomplete final write; investigate before recovery')
            break
        valid.append(line.rstrip(b'\n')+b'\n')
    output.write_bytes(b''.join(valid))
    output.with_suffix(output.suffix+'.provenance.json').write_text(json.dumps({'original':str(source.resolve()),'retained_records':len(valid),'discarded_incomplete_tail':len(valid)<len(lines)},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();recover(a.source,a.output)
