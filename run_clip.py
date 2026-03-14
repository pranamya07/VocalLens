import sqlite3
import os
import torch
import open_clip
from PIL import Image

print("Loading CLIP model...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai')
model = model.to(device)
model.eval()
tokenizer = open_clip.get_tokenizer('ViT-B-32')

labels = [
    "dog", "cat", "bird", "fish", "horse", "elephant", "lion",
    "person", "people", "group of people", "baby", "child", "crowd",
    "wedding", "birthday party", "graduation", "vacation", "beach",
    "mountain", "forest", "city", "indoor", "outdoor", "night",
    "food", "cake", "flowers", "tree", "car", "building",
    "happy", "smiling", "sad", "celebration", "selfie", "portrait",
    "sunset", "water", "sky", "snow", "rain",
    "family", "friends", "couple"
]

print("Encoding labels...")
text_tokens = tokenizer(labels).to(device)
with torch.no_grad():
    text_features = model.encode_text(text_tokens)
    text_features /= text_features.norm(dim=-1, keepdim=True)

conn = sqlite3.connect('database.db')
c = conn.cursor()
c.execute("SELECT id, path FROM images")
rows = c.fetchall()
print(f"Found {len(rows)} images in DB")

updated = 0
threshold = 23.0

for i, (img_id, path) in enumerate(rows):
    if not path or not os.path.exists(path):
        print(f"Skipping missing: {path}")
        continue
    try:
        image = preprocess(Image.open(path).convert("RGB")).unsqueeze(0).to(device)
        with torch.no_grad():
            image_features = model.encode_image(image)
            image_features /= image_features.norm(dim=-1, keepdim=True)
            similarities = (100.0 * image_features @ text_features.T).squeeze(0)

        scores = list(enumerate(similarities.tolist()))
        scores.sort(key=lambda x: x[1], reverse=True)

        if i == 0:
            print("Sample scores for first image:")
            for j, score in scores[:5]:
                print(f"  {labels[j]}: {score:.2f}")

        matched = [labels[j] for j, score in scores[:3] if score > threshold]

        if matched:
            c.execute("SELECT tags FROM images WHERE id = ?", (img_id,))
            existing = c.fetchone()[0] or ''
            existing_tags = [t.strip() for t in existing.split(',') if t.strip()]
            all_tags = list(set(existing_tags + matched))
            new_tags = ', '.join(all_tags)
            c.execute("UPDATE images SET tags = ? WHERE id = ?", (new_tags, img_id))
            updated += 1

        if (i + 1) % 20 == 0:
            conn.commit()
            print(f"  {i+1}/{len(rows)} done...")

    except Exception as e:
        print(f"  Skipped {path}: {e}")
        continue

conn.commit()
conn.close()
print(f"\nDone! Updated {updated} images with CLIP tags.")
print("Restart Flask and try searching 'dog' or 'happy' or 'beach'")