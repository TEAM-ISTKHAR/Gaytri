import os
import re

import aiofiles
import aiohttp
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from unidecode import unidecode
from youtubesearchpython.future import Video

from MecoMusic import YouTube, app
from config import YOUTUBE_IMG_URL


def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    newImage = image.resize((newWidth, newHeight))
    return newImage

def circle(img): 
     h,w=img.size 
     a = Image.new('L', [h,w], 0) 
     b = ImageDraw.Draw(a) 
     b.pieslice([(0, 0), (h,w)], 0, 360, fill = 255,outline = "white") 
     c = np.array(img) 
     d = np.array(a) 
     e = np.dstack((c, d)) 
     return Image.fromarray(e)


def clear(text):
    list = text.split(" ")
    title = ""
    for i in list:
        if len(title) + len(i) < 60:
            title += " " + i
    return title.strip()


async def get_thumb(videoid,user_id):
    final_path = f"cache/{videoid}_{user_id}.png"
    raw_thumb_path = f"cache/thumb{videoid}.png"
    thumbnail = YOUTUBE_IMG_URL

    if os.path.isfile(final_path):
        return final_path

    try:
        try:
            result = await Video.get(videoid)
        except:
            result = None
        if result and result.get("title"):
            try:
                title = result["title"]
                title = re.sub(r"\W+", " ", title)
                title = title.title()
            except:
                title = "Unsupported Title"
            try:
                duration = (result.get("duration") or {}).get("text") or "Unknown Mins"
            except:
                duration = "Unknown Mins"
            for thumb in result.get("thumbnails") or []:
                if isinstance(thumb, dict) and thumb.get("url"):
                    thumbnail = thumb["url"].split("?")[0]
                    break
            try:
                views = (result.get("viewCount") or {}).get("short") or "Unknown Views"
            except:
                views = "Unknown Views"
            try:
                channel = (result.get("channel") or {}).get("name") or "Unknown Channel"
            except:
                channel = "Unknown Channel"
        else:
            title, duration, _, thumbnail, _ = await YouTube.details(videoid, True)
            title = re.sub(r"\W+", " ", title).title()
            views = "Unknown Views"
            channel = "Unknown Channel"

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(raw_thumb_path, mode="wb")
                    await f.write(await resp.read())
                    await f.close()
                else:
                    return thumbnail

        sp = None
        for target_id in (user_id, app.id):
            try:
                async for photo in app.get_chat_photos(target_id, limit=1):
                    sp = await app.download_media(
                        photo.file_id, file_name=f"cache/{target_id}.jpg"
                    )
                    break
            except:
                continue
            if sp:
                break

        youtube = Image.open(raw_thumb_path).convert("RGBA")
        image1 = changeImageSize(1280, 720, youtube)
        image2 = image1.convert("RGBA")
        background = image2.filter(filter=ImageFilter.BoxBlur(10))
        enhancer = ImageEnhance.Brightness(background)
        background = enhancer.enhance(0.5)
        y=changeImageSize(200,200,circle(youtube)) 
        background.paste(y,(45,225),mask=y)
        if sp and os.path.isfile(sp):
            xp = Image.open(sp).convert("RGBA")
            a=changeImageSize(200,200,circle(xp)) 
            background.paste(a,(1045,225),mask=a)
        draw = ImageDraw.Draw(background)
        arial = ImageFont.truetype("MecoMusic/assets/font2.ttf", 30)
        font = ImageFont.truetype("MecoMusic/assets/font.ttf", 30)
        draw.text((1110, 8), unidecode(app.name), fill="white", font=arial)
        draw.text(
                (55, 560),
                f"{channel} | {views[:23]}",
                (255, 255, 255),
                font=arial,
            )
        draw.text(
                (57, 600),
                clear(title),
                (255, 255, 255),
                font=font,
            )
        draw.line(
                [(55, 660), (1220, 660)],
                fill="white",
                width=5,
                joint="curve",
            )
        draw.ellipse(
                [(918, 648), (942, 672)],
                outline="white",
                fill="white",
                width=15,
            )
        draw.text(
                (36, 685),
                "00:00",
                (255, 255, 255),
                font=arial,
            )
        draw.text(
                (1185, 685),
                f"{duration[:23]}",
                (255, 255, 255),
                font=arial,
            )
        try:
            os.remove(raw_thumb_path)
        except:
            pass
        background.save(final_path)
        return final_path
    except Exception:
        if os.path.isfile(raw_thumb_path):
            return raw_thumb_path
        return thumbnail
