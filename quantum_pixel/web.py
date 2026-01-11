#cSpell:ignore stegano
"""Website with fastapi"""
import shutil
import uuid
import os
import time
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor #pylint: disable=no-name-in-module
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from PIL import Image

from . import Generator, Steganography

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_DIR = os.path.join(PROJECT_ROOT, "static", "images")
os.makedirs(IMAGE_DIR, exist_ok=True)


async def cleanup_worker():
    """For every 1 hour, delete uploaded files with lifespan of 1 hour. This prevent everything."""
    try:
        while True:
            try:
                for name in os.listdir(IMAGE_DIR):
                    path = os.path.join(IMAGE_DIR, name)
                    if time.time() - os.path.getmtime(path) > 3600:
                        os.remove(path)
            except FileNotFoundError:
                pass
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        return

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Lifespan of the app, on event startup and shutdown."""
    # startup event.
    asyncio.create_task(cleanup_worker())
    yield
    # Shutdown event.
    executor.shutdown(cancel_futures=True)
    for name in os.listdir(IMAGE_DIR):
        path = os.path.join(IMAGE_DIR, name)
        os.remove(path)

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=os.path.join(PROJECT_ROOT, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(PROJECT_ROOT, "templates"))
executor = ThreadPoolExecutor()



### ------------------------ Welcome to my shit ------------------------------------



@app.get("/", response_class=HTMLResponse)
async def start(request: Request):
    """A default start on app."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/", response_class=RedirectResponse)
async def upload(request: Request):
    """Upload the file, then encode or decode depend on selection."""
    form = await request.form()
    file = form.get("file")

    if file.size > 1_073_741_824: # Im poor u know lol
        return templates.TemplateResponse("index.html",
                                          {"request": request, "error": "File should be under 1GB"})
    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
        return templates.TemplateResponse("index.html",
                                          {"request": request, "error": "Unsupported file type."})

    filename = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(IMAGE_DIR, filename), "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return RedirectResponse(f"/{form.get("upload_type")}/{filename}", status_code=303)

@app.get("/encode/{img}", response_class=HTMLResponse)
async def start_encode(request: Request, img: str):
    """Start the encode html."""
    if not os.path.exists(os.path.join(IMAGE_DIR, img)):
        return templates.TemplateResponse("encode.html", {"request": request, "error": (
                "The image file cannot be found, please restart the system. "
                "If it continues to happen, install the local version.")})
    json_path = os.path.join(IMAGE_DIR, f"{os.path.splitext(img)[0]}.json")
    if os.path.exists(json_path):
        with open(json_path, "rt", encoding="utf-8") as f:
            json_data: dict = json.load(f)
            f.close()
        return templates.TemplateResponse("encode.html", {"request": request, "filename": img,
                "preview": templates.get_template("encode_panel.html").render({
                        "filename": json_data.get("preview"),
                        "img_name": "preview"}),
                "steganography": templates.get_template("encode_panel.html").render({
                        "filename": json_data.get("steganography"),
                        "img_name": "steganography"})})
    return templates.TemplateResponse("encode.html", {"request": request, "filename": img})

@app.post("/encode/{img}", response_class=HTMLResponse)
async def end_encode(request: Request, img: str):
    """This guy here gonna cook us dinner."""
    if not os.path.exists(os.path.join(IMAGE_DIR, img)):
        return """<h2>INTERNAL ERROR</h2><p>The image file cannot be found, please restart the \
system. If it continues to happen, install the local version.</p>"""

    form = await request.form()
    input_path = os.path.join(IMAGE_DIR, img)
    output_path = os.path.join(IMAGE_DIR, form.get("save_path"))

    json_path = os.path.join(IMAGE_DIR, f"{os.path.splitext(img)[0]}.json")

    generator = Generator(input_path)
    match form.get("selected"):
        case "panel_preview":
            try:
                preview_img = await asyncio.get_event_loop().run_in_executor(
                    executor, generator.preview, float(form.get("intensity")))
            except AssertionError as err:
                return templates.TemplateResponse("encode.html",
                                            {"request": request, "filename": img, "error": err})
            preview_img.save(output_path)

            json_data: dict = {}
            if os.path.exists(json_path):
                json_data = json.load(open(json_path, "rt", encoding="utf-8"))

            with open(json_path, "wt", encoding="utf-8") as f:
                json_data.update({"preview": form.get("save_path")})
                json.dump(json_data, f)
                f.close()
            return templates.TemplateResponse("encode_panel.html",
                {"request": request, "filename": form.get("save_path"), "img_name": "preview"})

        case "panel_steganography":
            if await asyncio.get_event_loop().run_in_executor(executor, Steganography.encode,
                    Image.open(form.get("disguise").file), Image.open(input_path), output_path):
                json_data: dict = {}
                if os.path.exists(json_path):
                    json_data = json.load(open(json_path, "rt", encoding="utf-8"))

                with open(json_path, "wt", encoding="utf-8") as f:
                    json_data.update({"steganography": form.get("save_path")})
                    json.dump(json_data, f)
                    f.close()
                return templates.TemplateResponse("encode_panel.html",
                    {"request": request, "filename": form.get("save_path"), "img_name": "stegano"})
            return templates.TemplateResponse("encode.html",
                {"request": request, "filename": img, "error": (
                    "Cannot encode the image within. Try to decrease the size of real image "
                    "size or increase the size of the disguise image.")})

@app.get("/decode/{img}", response_class=HTMLResponse)
async def start_decode(request: Request, img: str):
    """Start the decode html."""
    if not os.path.exists(os.path.join(IMAGE_DIR, img)):
        return templates.TemplateResponse("decode.html", {"request": request, "error": (
                "The image file cannot be found, please restart the system. "
                "If it continues to happen, install the local version.")})
    return templates.TemplateResponse("decode.html", {"request": request})

@app.post("/decode/{img}", response_class=HTMLResponse)
async def end_decode(request: Request, img: str):
    """And this guys serve it with fire."""
    if not os.path.exists(os.path.join(IMAGE_DIR, img)):
        return templates.TemplateResponse("decode.html", {"request": request, "error": (
                "The image file cannot be found, please restart the system. "
                "If it continues to happen, install the local version.")})

    payload = await request.json()
    input_path = os.path.join(IMAGE_DIR, img)
    output_path = os.path.join(IMAGE_DIR, payload.get("save_path"))

    json_path = os.path.join(IMAGE_DIR, f"{os.path.splitext(img)[0]}.json")

    # Already got worked.
    if os.path.exists(json_path):
        with open(json_path, "rt", encoding="utf-8") as f:
            json_data: dict = json.load(f)
            f.close()
        if json_data.get("filename"):
            return templates.TemplateResponse("decode.html", {"request": request,
                                                          "filename": json_data["filename"]})

    # New thingy.
    if await asyncio.get_event_loop().run_in_executor(executor, Steganography.decode,
                                                      Image.open(input_path), output_path):
        os.remove(input_path)
        with open(json_path, "wt", encoding="utf-8") as f:
            json.dump({"filename": payload.get("save_path")}, f)
            f.close()
        return templates.TemplateResponse("decode.html", {"request": request,
                                                          "filename": payload.get("save_path")})
    os.remove(input_path)
    return templates.TemplateResponse("decode.html", {"request": request, "error": (
        "This image cannot be decoded. If you encoded with the provided tools, "
        "email me or create a Github issue and I will see what can be assisted."
    )})

@app.post("/remove/{img}")
async def remove(img: str):
    """Remove file when user exit."""
    scr_path = os.path.join(IMAGE_DIR, img)
    if os.path.exists(scr_path):
        os.remove(scr_path)

    json_path = os.path.join(IMAGE_DIR, f"{os.path.splitext(img)[0]}.json")
    if not os.path.exists(json_path):
        return
    with open(json_path, "rt", encoding="utf-8") as f:
        json_data: dict = json.load(f)
        f.close()
    if os.path.exists(json_path):
        os.remove(json_path)

    for path in json_data.values():
        img_path = os.path.join(IMAGE_DIR, path)
        if os.path.exists(img_path):
            os.remove(img_path)
