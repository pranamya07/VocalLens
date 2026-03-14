import sqlite3, os, json, re
from datetime import datetime

conn = sqlite3.connect('database.db')
c = conn.cursor()
c.execute('DELETE FROM images')

samples_dir = 'static/samples'
inserted = 0

folder_tags = {
    'good days with fam': 'family, friends, hangout, together, fam, people, outdoor, fun',
    'photos from 2025': '2025, recent, photos, memories',
    'photos from 2026': '2026, recent, photos, memories',
    'potential pfps': 'portrait, selfie, profile, face, pfp, person',
}

def extract_date(filename):
    # Match YYYYMMDD at start of filename
    match = re.match(r'(\d{4})(\d{2})(\d{2})', filename)
    if match:
        y, m, d = match.groups()
        try:
            return datetime(int(y), int(m), int(d)).strftime('%B %d, %Y')
        except Exception:
            pass
    # Match IMG_YYYYMMDD
    match = re.search(r'IMG_(\d{4})(\d{2})(\d{2})', filename)
    if match:
        y, m, d = match.groups()
        try:
            return datetime(int(y), int(m), int(d)).strftime('%B %d, %Y')
        except Exception:
            pass
    return ''

for root, dirs, files in os.walk(samples_dir):
    for filename in files:
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            continue
        full_path = os.path.join(root, filename).replace('\\', '/')
        parts = full_path.split('/')
        folder_name = parts[2].lower() if len(parts) > 2 else ''
        tags = folder_tags.get(folder_name, folder_name)
        date = extract_date(filename)
        c.execute(
            'INSERT INTO images (filename, path, tags, date, location, faces, objects, scene, quality, analyzed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (filename, full_path, tags, date, folder_name, '[]', '[]', 'unknown', 0.8, 1)
        )
        inserted += 1

conn.commit()
conn.close()
print(f'Inserted {inserted} images')