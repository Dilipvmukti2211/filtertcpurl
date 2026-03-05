from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import pathlib
import csv
import re

BASE_PATH = pathlib.Path("/home/dilip/provisioning")

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

unmatched_data = []


# -------- Extract middle number --------

def extract_number(value):
    m = re.search(r'(\d+)', value)
    return m.group(1) if m else None


# -------- Load all TXT files --------

def load_txt_data():

    uuid_map = {}
    number_map = {}

    for file in BASE_PATH.rglob("*.txt"):

        with file.open(errors="ignore") as f:

            for line in f:

                parts = line.strip().split()

                if len(parts) >= 2:

                    uuid = parts[0].strip().upper()
                    url = parts[-1].strip()

                    if url.startswith("tcp://"):

                        uuid_map[uuid] = url

                        number = extract_number(uuid)

                        if number:
                            number_map[number] = (uuid, url)

    return uuid_map, number_map


@app.get("/")
def home():
    return FileResponse("static/index.html")


# -------- Single UUID Search --------

@app.get("/search")

def search(uuid: str = Query(...)):

    uuid_map, number_map = load_txt_data()

    value = uuid.strip().upper()

    # Exact UUID match
    if value in uuid_map:

        return {
            "uuid": value,
            "tcp_url": uuid_map[value],
            "match_type": "exact"
        }

    number = extract_number(value)

    # VSPL-140993 type
    if number and number in number_map:

        correct_uuid, url = number_map[number]

        return {
            "uuid": correct_uuid,
            "tcp_url": url,
            "match_type": "number_match"
        }

    # Only number search
    if value.isdigit() and value in number_map:

        correct_uuid, url = number_map[value]

        return {
            "uuid": correct_uuid,
            "tcp_url": url,
            "match_type": "number_only"
        }

    return {"error": "No Match Found"}


# -------- CSV Upload --------

@app.post("/upload")

async def upload(file: UploadFile = File(...)):

    global unmatched_data

    content = await file.read()

    lines = content.decode(errors="ignore").splitlines()

    input_uuids = [l.strip() for l in lines if l.strip()]

    uuid_map, number_map = load_txt_data()

    matched = []
    unmatched_data = []

    for u in input_uuids:

        key = u.upper()

        if key in uuid_map:

            number = extract_number(u)

            matched.append([u, number, uuid_map[key]])

        else:

            number = extract_number(u)

            unmatched_data.append([u, number])

    with open("matched.csv", "w", newline="") as f:

        writer = csv.writer(f)

        writer.writerow(["uuid", "number", "tcp_url"])

        writer.writerows(matched)

    return JSONResponse({
        "matched": len(matched),
        "unmatched": unmatched_data
    })


# -------- Download Matched CSV --------

@app.get("/download-matched")

def download():

    return FileResponse("matched.csv", filename="matched.csv")


# -------- Generate Unmatched CSV --------

@app.get("/generate-unmatched")

def generate_unmatched():

    uuid_map, number_map = load_txt_data()

    result = []

    for uuid, number in unmatched_data:

        if number in number_map:

            correct_uuid, url = number_map[number]

            result.append([correct_uuid, number, url])

        else:

            result.append([uuid, number, "NOT_FOUND"])

    with open("unmatched.csv", "w", newline="") as f:

        writer = csv.writer(f)

        writer.writerow(["uuid", "number", "tcp_url"])

        writer.writerows(result)

    return FileResponse("unmatched.csv", filename="unmatched.csv")
