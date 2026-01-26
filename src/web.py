#cSpell:ignore stegano
"""Website with fastapi"""
import shutil
import uuid
import os
import time
import json
import asyncio
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from PIL import Image

from . import Generator, Steganography

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
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
    allow_credentials=True,
    allow_methods=["POST"],
    max_age=100,
)
app.mount("/static", StaticFiles(directory=os.path.join(PROJECT_ROOT, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(PROJECT_ROOT, "templates"))
executor = ThreadPoolExecutor()
background_task: dict = {}

def _remove_from_list(uid: str):
    background_task.pop(uid, None)



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

    if not file or not form.get("upload_type"):
        return templates.TemplateResponse("index.html",
                                          {"request": request, "error": "Unable to load form."})

    # Im poor u know lol. You can delete this line, just acknowledge your cpu power.
    if file.size > 1_073_741_824:
        return templates.TemplateResponse("index.html",
                                          {"request": request, "error": "File should be <1GB."})
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
            if input_path and form.get("intensity") and form.get("save_path"):
                try:
                    uid: str = uuid.uuid4().hex
                    future_item = asyncio.get_event_loop().run_in_executor(
                        executor, generator.preview, float(form.get("intensity")))
                    future_item.add_done_callback(lambda _: _remove_from_list(uid))
                    background_task.update({uid: future_item})

                    json_data: dict = {}
                    if os.path.exists(json_path):
                        json_data = json.load(open(json_path, "rt", encoding="utf-8"))
                    json_data.update({"uid": uid})
                    with open(json_path, "wt", encoding="utf-8") as f:
                        json.dump(json_data, f)
                        f.close()

                    preview_img = await future_item
                except asyncio.exceptions.CancelledError:
                    return templates.TemplateResponse("encode.html",
                            {"request": request, "filename": img, "error": "User exited."})
                except AssertionError as err:
                    return templates.TemplateResponse("encode.html",
                                                {"request": request, "filename": img, "error": err})
                preview_img.save(output_path)

                with open(json_path, "wt", encoding="utf-8") as f:
                    json_data.update({"preview": form.get("save_path")})
                    json.dump(json_data, f)
                    f.close()
                return templates.TemplateResponse("encode_panel.html",
                    {"request": request, "filename": form.get("save_path"), "img_name": "preview"})

        case "panel_steganography":
            if input_path and form.get("disguise") and form.get("save_path"):
                uid: str = uuid.uuid4().hex
                future_item=asyncio.get_event_loop().run_in_executor(executor, Steganography.encode,
                    Image.open(form.get("disguise").file), Image.open(input_path), output_path)
                future_item.add_done_callback(lambda _: _remove_from_list(uid))
                background_task.update({uid: future_item})

                json_data: dict = {}
                if os.path.exists(json_path):
                    json_data = json.load(open(json_path, "rt", encoding="utf-8"))
                json_data.update({"uid": uid})
                with open(json_path, "wt", encoding="utf-8") as f:
                    json.dump(json_data, f)
                    f.close()

                try:
                    if await future_item:
                        with open(json_path, "wt", encoding="utf-8") as f:
                            json_data.update({"steganography": form.get("save_path")})
                            json.dump(json_data, f)
                            f.close()
                        return templates.TemplateResponse("encode_panel.html", {"request": request,
                                "filename": form.get("save_path"), "img_name": "stegano"})
                except asyncio.exceptions.CancelledError:
                    return templates.TemplateResponse("encode.html",
                            {"request": request, "filename": img, "error": "User exited."})
                return templates.TemplateResponse("encode.html",
                    {"request": request, "filename": img, "error": (
                        "Cannot encode the image within. Try to decrease the size of real image "
                        "size or increase the size of the disguise image.")})

    return templates.TemplateResponse("encode.html",
                        {"request": request, "filename": img, "error": "Unable to load form."})

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

    if not payload.get("save_path"):
        return templates.TemplateResponse("decode.html",
                        {"request": request, "filename": img, "error": "Unable to load payload."})


    uid: str = uuid.uuid4().hex
    future_item = asyncio.get_event_loop().run_in_executor(executor, Steganography.decode,
        Image.open(input_path), output_path)
    future_item.add_done_callback(lambda _: _remove_from_list(uid))
    background_task.update({uid: future_item})

    with open(json_path, "wt", encoding="utf-8") as f:
        json.dump({"uid": uid}, f)
        f.close()

    try:
        if await future_item:
            os.remove(input_path)
            with open(json_path, "wt", encoding="utf-8") as f:
                json.dump({"filename": payload.get("save_path")}, f)
                f.close()
            return templates.TemplateResponse("decode.html",
                                        {"request": request, "filename": payload.get("save_path")})
        os.remove(input_path)
    except asyncio.exceptions.CancelledError:
        return templates.TemplateResponse("encode.html",
                {"request": request, "filename": img, "error": "User exited."})
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

    try:
        background_task.get(json_data.pop("uid_", json_data.pop("uid"))).cancel()
    except AttributeError:
        pass
    for path in json_data.values():
        img_path = os.path.join(IMAGE_DIR, path)
        if os.path.exists(img_path):
            os.remove(img_path)
