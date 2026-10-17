"""Export the reviewed lantern inputs; native Kodi labels provide typography."""
from pathlib import Path
from PIL import Image
import argparse
B=Path(__file__).parent
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=B.parents[1]/'addon/resources/media');args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
for direction in ('previous','next'):
    im=Image.open(B/f'lantern-{direction}-orbit.png').convert('RGBA')
    im.thumbnail((512,512),Image.Resampling.LANCZOS)
    im.save(args.output/f'page-{direction}.png')
