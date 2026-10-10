"""Encode previews from the approved pet atlas."""
import argparse
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

import imageio_ffmpeg

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--atlas', type=Path, default=root / 'outputs/zhuobielin-pet.png')
parser.add_argument('--output-dir', type=Path, default=root / 'outputs')
parser.add_argument('--font', default='/System/Library/Fonts/STHeiti Medium.ttc')
args = parser.parse_args()
run = root / 'work/preview-cache'
out = args.output_dir.expanduser().resolve()
out.mkdir(parents=True, exist_ok=True)
atlas_path = args.atlas.expanduser().resolve()
atlas = Image.open(atlas_path).convert('RGBA')
if atlas.size != (1536,2288):
    raise SystemExit('Expected a 1536x2288 v2 pet atlas.')
counts = [6,8,8,4,5,8,6,6,6,8,8]
names = ["idle", "running-right", "running-left", "waving", "jumping", "failed", "waiting", "running", "review", "look-a", "look-b"]
config = json.loads((root / 'pet.json').read_text())
actions = {action['state']: action for action in config['actions']}
display_names = [actions[state]['name'] for state in names[:9]]
font = ImageFont.truetype(args.font, 16)
# Match the desktop player's fixed timing rather than slowing previews separately.
durations = [[1680,660,660,840,840,1920], [120]*7+[220], [120]*7+[220], [140]*3+[280], [140]*4+[280], [140]*7+[240], [150]*5+[260], [120]*5+[220], [150]*5+[280], [180]*8, [180]*8]
final_frames = run / "qa/final-frames"
rows = []
for row, count in enumerate(counts):
    cells = [atlas.crop((col*192,row*208,(col+1)*192,(row+1)*208)) for col in range(count)]
    rows.append(cells)
    folder = final_frames / names[row]
    folder.mkdir(parents=True,exist_ok=True)
    for i, cell in enumerate(cells):
        cell.save(folder / f"{i:02d}.png")

def gif(frames, durations_ms, path):
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations_ms, loop=0, disposal=2, optimize=False)

def video(frames, durations_ms, path, fps=25):
    writer=imageio_ffmpeg.write_frames(str(path), frames[0].size, fps=fps, codec="libx264", pix_fmt_in="rgb24", pix_fmt_out="yuv420p", macro_block_size=1, output_params=["-movflags", "+faststart"])
    writer.send(None)
    for frame, ms in zip(frames,durations_ms):
        for _ in range(max(1,round(ms*fps/1000))):
            writer.send(frame.convert("RGB").tobytes())
    writer.close()

def labeled(cell, label):
    frame = Image.new("RGB", (384,448), (247,243,234))
    frame.paste(cell.resize((384,416), Image.Resampling.LANCZOS),(0,28),cell.resize((384,416),Image.Resampling.LANCZOS))
    ImageDraw.Draw(frame).text((12,4),label,fill=(65,52,44),font=font)
    return frame

all_frames=[]
all_durations=[]
for row in range(9):
    all_frames.extend([labeled(c,display_names[row]) for c in rows[row]])
    all_durations.extend(durations[row])
gif(all_frames, all_durations, out / "all-actions.gif")
video(all_frames, all_durations, out / "all-actions.mp4",fps=50)
for row in range(9):
    folder=out/"animations"
    folder.mkdir(exist_ok=True)
    gif(rows[row],durations[row],folder/f"{names[row]}.gif")
transition=rows[0]+rows[4]+rows[0]
gif(transition,durations[0]+durations[4]+durations[0],out / "idle-jump-idle.gif")
gif(rows[0]+rows[3]+rows[0],durations[0]+durations[3]+durations[0],out / "idle-welcome-idle.gif")
gif(rows[9]+rows[10],durations[9]+durations[10],out / "look-loop.gif")
gif(rows[4],durations[4],out / "belly-roll.gif")
gif(rows[7],durations[7],out / "hunting.gif")
gif(rows[6],durations[6],out / "post-scratch.gif")
for row,name in [(7,'hunting'),(6,'post-scratch')]:
    gif([c.resize((384,416),Image.Resampling.LANCZOS) for c in rows[row]],durations[row],out/f'{name}-large.gif')
gif(rows[8],durations[8],out / "gobang-back.gif")
labels=[(4,2,"悬停：露肚皮"),(7,3,"工作中：猛扑"),(3,1,"欢迎：起跳"),(5,2,"失败：思考")]
stills=Image.new("RGB",(768,240),(247,243,234))
for i,(r,c,l) in enumerate(labels):
    ImageDraw.Draw(stills).text((i*192+6,4),l,fill=(65,52,44),font=font)
    stills.paste(rows[r][c],(i*192,28),rows[r][c])
stills.save(out / "four-action-stills.png")
demo_frames=[]
for c in rows[8]:
    demo=Image.new("RGB",(384,240),(247,243,234))
    draw=ImageDraw.Draw(demo)
    draw.rectangle((192,0,384,240),fill=(42,46,54))
    draw.text((8,4),"浅色桌面",fill=(65,52,44),font=font)
    draw.text((200,4),"深色桌面",fill=(242,236,224),font=font)
    demo.paste(c,(0,28),c)
    demo.paste(c,(192,28),c)
    demo_frames.append(demo)
gif(demo_frames,durations[8],out / "transparent-preview.gif")
demo_frames[0].save(out / "transparent-preview.png")
base=rows[0][0]
base.save(out / "base-pet.png")
print(json.dumps({'atlas_source':str(atlas_path),'output_dir':str(out),'preview_frames':sum(counts)},indent=2))
