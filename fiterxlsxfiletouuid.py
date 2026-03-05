import pandas as pd
import re
import csv

input_file = "West Bengal Packing 2025 (3).xlsx"
output_file = "camera_did.csv"

pattern = r"[A-Z]{4}-\d{6}-[A-Z]{5}"

camera_ids = []

# पूरी excel read करो (header assume नहीं करेंगे)
df = pd.read_excel(input_file, header=None)

for row in df.values:
    for cell in row:
        if isinstance(cell, str):
            match = re.search(pattern, cell)
            if match:
                camera_ids.append(match.group())

# duplicates remove
camera_ids = list(dict.fromkeys(camera_ids))

# CSV write
with open(output_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["CAMERA_DID"])
    for cid in camera_ids:
        writer.writerow([cid])

print("CSV generated:", output_file)
