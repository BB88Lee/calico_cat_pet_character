"""Rebuild approved generated pixels with the installed Pets skill pipeline."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from statistics import median

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, default=Path('work/rebuild'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    skill = args.skill_dir.expanduser().resolve()
    output = args.output_dir.expanduser().resolve()
    qa = output / 'qa'
    qa.mkdir(parents=True, exist_ok=True)
    frames = output / 'frames'
    shutil.copytree(root / 'source/frames', frames, dirs_exist_ok=True)
    manifest = json.loads((frames / 'frames-manifest.json').read_text())
    for row in manifest['rows']:
        row['frames'] = [str(frames / row['state'] / f'{i:02d}.png')
                         for i in range(len(row['frames']))]
    (frames / 'frames-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    def bundled(name, *parameters):
        script = skill / 'scripts' / name
        if not script.is_file():
            raise SystemExit(f'Pets skill script missing: {script}')
        subprocess.run([sys.executable, str(script), *map(str, parameters)], check=True)

    bundled('inspect_frames.py', '--frames-root', frames, '--json-out', qa / 'review.json', '--require-components')
    bundled('compose_atlas.py', '--frames-root', frames, '--output', output / 'base.png')
    bundled('assemble_extended_atlas.py', '--base-atlas', output / 'base.png',
            '--registered-row-9', root / 'source/look/registered-row-9.png',
            '--row-9-registration', root / 'source/look/registration.json',
            '--look-row-10', root / 'source/strips/look-row-10.png',
            '--chroma-key', '#0000FF', '--output', output / 'raw.png')
    atlas = output / 'zhuobielin-pet.png'
    bundled('despill_chroma_edges.py', output / 'raw.png', '--output', atlas,
            '--json-out', qa / 'chroma-despill.json', '--chroma-key', '#0000FF')
    bundled('validate_atlas.py', atlas, '--require-v2', '--chroma-key', '#0000FF',
            '--json-out', qa / 'validation.json')
    bundled('make_contact_sheet.py', atlas, '--output', qa / 'contact-sheet-extended.png', '--scale', '1')
    bundled('make_direction_qa_sheet.py', atlas, '--output', qa / 'directions.png')
    bundled('measure_direction_continuity.py', atlas, '--json-out', qa / 'look-continuity.json')
    config = json.loads((root / 'pet.json').read_text())
    actions = config['actions']
    if actions[4].get('motion_family') == 'belly-roll':
        # The user explicitly moved the jump artwork to the welcome slot.
        # Check real jump geometry there; the hover slot now stays on the ground.
        image = Image.open(atlas).convert('RGBA')
        def baseline(row, column):
            cell = image.crop((column * 192, row * 208, (column + 1) * 192, (row + 1) * 208))
            return cell.getchannel('A').getbbox()[3]
        idle_baseline = round(median(baseline(0, i) for i in range(6)))
        welcome_baselines = [baseline(3, i) for i in range(4)]
        lift = max(welcome_baselines) - min(welcome_baselines)
        landing = abs(welcome_baselines[-1] - idle_baseline)
        mapping_review = {
            'ok': lift >= 8 and landing <= 12,
            'user_requested_mapping': {action['state']: action['name'] for action in actions},
            'welcome_jump': {'row': 3, 'baselines': welcome_baselines,
                             'airborne_lift_pixels': lift, 'landing_delta_pixels': landing},
            'hover_row_override': 'row 4 intentionally contains grounded belly-roll artwork',
            'quality_gate_note': 'default geometry checks retained; actual jump semantics verified in row 3',
        }
        (qa / 'custom-action-mapping.json').write_text(json.dumps(mapping_review, ensure_ascii=False, indent=2))
        if not mapping_review['ok']:
            raise SystemExit('Remapped welcome jump failed lift or landing checks')
    bundled('validate_pet_quality.py', atlas, '--atlas-validation', qa / 'validation.json',
            '--chroma-report', qa / 'chroma-despill.json', '--frame-review', qa / 'review.json',
            '--direction-semantics', root / 'qa/direction-semantics.json',
            '--continuity', qa / 'look-continuity.json', '--json-out', qa / 'pet-quality.json')
    print(json.dumps({'atlas': str(atlas), 'sha256': hashlib.sha256(atlas.read_bytes()).hexdigest()}, indent=2))


if __name__ == '__main__':
    main()
