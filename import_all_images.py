import sqlite3
import os
from pathlib import Path
import json

print("=" * 60)
print("📸 IMPORTING ALL IMAGES TO DATABASE")
print("=" * 60)

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Get list of images already in database
c.execute("SELECT filename FROM images")
existing = set(row[0] for row in c.fetchall())
print(f"📊 Existing database records: {len(existing)}")

# Walk through all image folders
samples_path = Path("static/samples")
image_extensions = ('.jpg', '.jpeg', '.png', '.gif')

new_images = 0
skipped = 0

for root, dirs, files in os.walk(samples_path):
    folder_name = os.path.basename(root)
    for file in files:
        if file.lower().endswith(image_extensions):
            if file in existing:
                skipped += 1
            else:
                # Generate tags based on folder name
                tags = [folder_name.lower().replace(' ', '_')]
                
                # Insert new image
                c.execute('''
                    INSERT INTO images 
                    (filename, path, tags, date, location, faces, objects, scene, quality, analyzed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    file,
                    os.path.join(root, file).replace('\\', '/'),
                    ', '.join(tags),
                    '',  # date unknown
                    '',  # location unknown
                    '[]',  # no faces detected yet
                    '[]',  # no objects detected yet
                    'unknown',  # scene
                    0.5,  # default quality
                    0  # not analyzed
                ))
                new_images += 1
                print(f"✅ Added: {folder_name}/{file}")

conn.commit()

# Final count
c.execute("SELECT COUNT(*) FROM images")
total = c.fetchone()[0]
print(f"\n📊 FINAL COUNTS:")
print(f"   Previously in database: {len(existing)}")
print(f"   Newly added: {new_images}")
print(f"   Skipped (duplicates): {skipped}")
print(f"   TOTAL NOW: {total} images")

conn.close()
print("\n🎉 All images imported! Run your app now.")