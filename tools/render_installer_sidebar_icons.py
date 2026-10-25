"""Reproduce small outline sidebar assets from code-owned vector paths.

Run from any directory with Python/Pillow. SVG sources are emitted beside PNGs
so future icon changes do not require editing raster assets.
"""
from pathlib import Path
from PIL import Image,ImageDraw
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/media'
WHITE='#EEF4F7';CYAN='#29D9EE'
ICONS={
 'updates':[
  (WHITE,[('M',(4,9)),('C',(5.4,4.3,10.7,2.3,15,4.3)),('C',(17.1,5.3,18.5,6.9,19.4,9))]),
  (CYAN,[('M',(19.4,4.6)),('L',(19.4,9)),('L',(15.0,9))]),
  (WHITE,[('M',(20,15)),('C',(18.6,19.7,13.3,21.7,9,19.7)),('C',(6.9,18.7,5.5,17.1,4.6,15))]),
  (CYAN,[('M',(4.6,19.4)),('L',(4.6,15)),('L',(9.0,15))])],
 'maintenance-wrench':[
  (WHITE,[('M',(14.6,6.3)),('L',(17.7,9.4)),('L',(21.4,5.7)),('C',(22.6,9.3,19.4,13.3,15.5,12.5)),('L',(7.0,21.0)),('C',(5.7,22.3,3.7,22.3,2.6,21.1)),('C',(1.5,19.9,1.7,18.3,2.9,17.1)),('L',(11.3,8.7)),('C',(10.4,5.0,14.1,1.8,17.7,2.8)),('L',(14.6,6.3))]),
  (CYAN,[('M',(5.1,18.6)),('L',(6.5,17.2))])]
}
def render(name,paths):
 scale=64;im=Image.new('RGBA',(24*scale,24*scale));draw=ImageDraw.Draw(im)
 tags=[]
 for color,commands in paths:
  points=[];cursor=(0,0)
  for command,args in commands:
   if command=='M':cursor=args;points.append(cursor)
   elif command=='L':cursor=args;points.append(cursor)
   elif command=='C':
    p0=cursor;p1=args[:2];p2=args[2:4];p3=args[4:]
    for n in range(1,33):
     t=n/32;u=1-t;points.append(tuple(u*u*u*p0[i]+3*u*u*t*p1[i]+3*u*t*t*p2[i]+t*t*t*p3[i] for i in (0,1)))
    cursor=p3
  coords=[(round(x*scale),round(y*scale)) for x,y in points];width=round(.95*scale)
  draw.line(coords,fill=color,width=width,joint='curve')
  radius=width/2
  for x,y in (coords[0],coords[-1]):draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=color)
  data=' '.join(cmd+' '+' '.join(map(str,values)) for cmd,values in commands)
  tags.append('<path d="'+escape(data)+'" fill="none" stroke="'+color+'" stroke-width="0.95" stroke-linecap="round" stroke-linejoin="round"/>')
 im.resize((256,256),Image.Resampling.LANCZOS).save(DEST/(name+'.png'))
 (DEST/(name+'.svg')).write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'+''.join(tags)+'</svg>\n')
if __name__=='__main__':
 for name,paths in ICONS.items():render(name,paths)
