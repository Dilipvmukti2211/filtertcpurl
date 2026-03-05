from fastapi import FastAPI, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Set
import pathlib
import io
import csv

BASE_PATH = pathlib.Path("/home/dilip/provisioning")

app = FastAPI(
    title="UUID → TCP URL Dashboard",
    version="7.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Device(BaseModel):
    uuid: str
    tcp_url: str
    source_file: str
    line_number: int


def search_uuids(uuids: Set[str]):
    results: List[Device] = []
    found: Set[str] = set()

    for file in BASE_PATH.rglob("*.txt"):
        try:
            with file.open("r", errors="ignore") as f:
                for lineno, line in enumerate(f, start=1):
                    line = line.strip()
                    parts = line.split()

                    if len(parts) >= 2:
                        u = parts[0]

                        if u in uuids and parts[-1].startswith("tcp://"):
                            found.add(u)

                            results.append(
                                Device(
                                    uuid=u,
                                    tcp_url=parts[-1],
                                    source_file=str(file.relative_to(BASE_PATH)),
                                    line_number=lineno
                                )
                            )
        except Exception:
            continue

    unmatched = list(uuids - found)

    return results, unmatched


# -------- SEARCH API --------

@app.get("/api/devices")
def get_devices(uuid: str = Query(...)):
    uuid_set = {u.strip() for u in uuid.split(",") if u.strip()}
    results, unmatched = search_uuids(uuid_set)

    return {
        "matched": results,
        "unmatched": unmatched
    }


# -------- CSV UPLOAD --------

@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):

    content = await file.read()
    lines = content.decode(errors="ignore").splitlines()

    uuid_set = {line.strip() for line in lines if line.strip()}

    results, unmatched = search_uuids(uuid_set)

    # matched CSV
    matched_file = pathlib.Path("matched_output.csv")

    with matched_file.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["uuid", "tcp_url", "source_file", "line_number"])

        for r in results:
            writer.writerow([r.uuid, r.tcp_url, r.source_file, r.line_number])

    return {
        "download": "/download/matched",
        "unmatched": unmatched
    }


@app.get("/download/matched")
def download_csv():
    return FileResponse(
        "matched_output.csv",
        media_type="text/csv",
        filename="output.csv"
    )


@app.get("/")
def dashboard():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
