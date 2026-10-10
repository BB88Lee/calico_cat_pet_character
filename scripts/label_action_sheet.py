"""Translate contact-sheet headers; retain every bundled-rendered pose pixel."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--qa-dir', type=Path, default=root / 'work/rebuild/qa')
parser.add_argument('--output-dir', type=Path, default=root / 'outputs')
parser.add_argument('--font', default='/System/Library/Fonts/STHeiti Medium.ttc')
args = parser.parse_args()
out = args.output_dir.expanduser().resolve()
out.mkdir(parents=True, exist_ok=True)
sheet = Image.open(args.qa_dir / 'contact-sheet-extended.png').convert('RGB')
font = ImageFont.truetype(args.font, 16)
names = [
    "眨眼和呼吸", "向右小跑", "向左小跑", "头朝下躺地上，露肚皮撒娇", "起跳和落地",
    "趴低盯视，扭屁股蓄力，突然猛扑", "肚子后腿贴柱，抓麻绳柱往上扽", "认真思考",
    "坐在五子棋棋盘上，露后背看窗外，轻轻动耳朵",
    "转头方向：上、右上、右、右下", "转头方向：下、左下、左、左上",
]
counts = [6,8,8,4,5,8,6,6,6,8,8]
draw = ImageDraw.Draw(sheet)
for row, name in enumerate(names):
    y = row * 230
    draw.rectangle((0,y,1535,y+21),fill="#111111")
    draw.text((6,y+2),f"{row+1}. {name}",font=font,fill="white")
    draw.text((1440,y+2),f"{counts[row]} 帧",font=font,fill="white")
sheet.save(out / "action-list-full.png")
sheet.crop((0,0,1536,2070)).save(out / "action-list.png")
