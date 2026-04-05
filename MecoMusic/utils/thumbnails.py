import os
import re

import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
from unidecode import unidecode
from ytSearch import VideosSearch

from MecoMusic import YouTube, app
from config import YOUTUBE_IMG_URL

CANVAS_SIZE = (1280, 720)
FRAME_RECT = (374, 118, 906, 626)
ART_RECT = (402, 146, 878, 452)
INFO_RECT = (392, 474, 888, 602)
TITLE_AREA_WIDTH = 316


def changeImageSize(maxWidth, maxHeight, image):
    return ImageOps.contain(
        image,
        (maxWidth, maxHeight),
        Image.Resampling.LANCZOS,
    )


def fit_image(image, size):
    return ImageOps.fit(
        image,
        size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def add_round_corners(image, radius):
    rounded = image.convert("RGBA")
    mask = Image.new("L", rounded.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        (0, 0, rounded.size[0], rounded.size[1]),
        radius=radius,
        fill=255,
    )
    output = Image.new("RGBA", rounded.size, (0, 0, 0, 0))
    output.paste(rounded, (0, 0), mask)
    return output


def circle(image, size):
    avatar = fit_image(image.convert("RGBA"), (size, size))
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(avatar, (0, 0), mask)
    return output


def clear(text):
    list = text.split(" ")
    title = ""
    for i in list:
        if len(title) + len(i) < 60:
            title += " " + i
    return title.strip()


def load_font(name, size):
    try:
        return ImageFont.truetype(f"MecoMusic/assets/{name}", size)
    except Exception:
        return ImageFont.load_default()


def truncate_text(draw, text, font, max_width):
    text = unidecode(clear(text or "")) or "Unknown Title"
    if draw.textlength(text, font=font) <= max_width:
        return text
    ellipsis = "..."
    while text and draw.textlength(f"{text}{ellipsis}", font=font) > max_width:
        text = text[:-1]
    return f"{text.rstrip()}{ellipsis}" if text else ellipsis


def add_glow_layer():
    glow_layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow_layer)
    draw.ellipse((70, 360, 530, 770), fill=(255, 112, 72, 82))
    draw.ellipse((710, 40, 1140, 380), fill=(94, 182, 255, 56))
    draw.ellipse((600, 430, 1160, 860), fill=(255, 196, 108, 40))
    return glow_layer.filter(ImageFilter.GaussianBlur(90))


def add_shadow(rect, radius, blur, offset=(0, 18)):
    shadow = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    x1, y1, x2, y2 = rect
    ox, oy = offset
    draw.rounded_rectangle(
        (x1 + ox, y1 + oy, x2 + ox, y2 + oy),
        radius=radius,
        fill=(0, 0, 0, 135),
    )
    return shadow.filter(ImageFilter.GaussianBlur(blur))


async def get_thumb(videoid,user_id):
    final_path = f"cache/{videoid}_{user_id}.png"
    raw_thumb_path = f"cache/thumb{videoid}.png"
    thumbnail = YOUTUBE_IMG_URL
    os.makedirs("cache", exist_ok=True)

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

        requester_photo = None
        fallback_photo = None
        for target_id in (user_id, app.id):
            downloaded_photo = None
            try:
                async for photo in app.get_chat_photos(target_id, limit=1):
                    downloaded_photo = await app.download_media(
                        photo.file_id, file_name=f"cache/{target_id}.jpg"
                    )
                    break
            except:
                continue
            if target_id == user_id and downloaded_photo:
                requester_photo = downloaded_photo
            elif target_id == app.id and downloaded_photo:
                fallback_photo = downloaded_photo

        youtube = Image.open(raw_thumb_path).convert("RGBA")
        background = fit_image(youtube, CANVAS_SIZE)
        background = background.filter(ImageFilter.GaussianBlur(24))
        background = ImageEnhance.Brightness(background).enhance(0.36)
        background = ImageEnhance.Color(background).enhance(0.82)

        canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 255))
        canvas.alpha_composite(background)
        canvas.alpha_composite(Image.new("RGBA", CANVAS_SIZE, (10, 12, 18, 116)))
        canvas.alpha_composite(add_glow_layer())
        canvas.alpha_composite(add_shadow(FRAME_RECT, radius=40, blur=28))
        canvas.alpha_composite(add_shadow(ART_RECT, radius=28, blur=18, offset=(0, 12)))

        frame_layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
        frame_draw = ImageDraw.Draw(frame_layer)
        frame_draw.rounded_rectangle(
            FRAME_RECT,
            radius=40,
            fill=(255, 255, 255, 54),
            outline=(255, 255, 255, 176),
            width=2,
        )
        frame_draw.rounded_rectangle(
            (FRAME_RECT[0] + 12, FRAME_RECT[1] + 12, FRAME_RECT[2] - 12, FRAME_RECT[3] - 12),
            radius=32,
            fill=(255, 255, 255, 12),
        )
        canvas.alpha_composite(frame_layer)

        artwork_size = (ART_RECT[2] - ART_RECT[0], ART_RECT[3] - ART_RECT[1])
        artwork = add_round_corners(fit_image(youtube, artwork_size), 28)
        canvas.alpha_composite(artwork, (ART_RECT[0], ART_RECT[1]))

        info_layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
        info_draw = ImageDraw.Draw(info_layer)
        info_draw.rounded_rectangle(
            INFO_RECT,
            radius=26,
            fill=(44, 44, 52, 196),
            outline=(255, 255, 255, 58),
            width=1,
        )
        info_draw.rounded_rectangle(
            (INFO_RECT[0], INFO_RECT[1], INFO_RECT[2], INFO_RECT[1] + 28),
            radius=26,
            fill=(255, 255, 255, 12),
        )

        duration_rect = (ART_RECT[2] - 136, ART_RECT[1] + 18, ART_RECT[2] - 18, ART_RECT[1] + 64)
        views_rect = (ART_RECT[0] + 18, ART_RECT[3] - 58, ART_RECT[0] + 168, ART_RECT[3] - 16)
        brand_rect = (ART_RECT[0] + 18, ART_RECT[1] + 18, ART_RECT[0] + 164, ART_RECT[1] + 58)

        for rect in (duration_rect, views_rect, brand_rect):
            info_draw.rounded_rectangle(
                rect,
                radius=18,
                fill=(12, 14, 18, 182),
                outline=(255, 255, 255, 68),
                width=1,
            )
        canvas.alpha_composite(info_layer)

        avatar_source = youtube
        if requester_photo and os.path.isfile(requester_photo):
            avatar_source = Image.open(requester_photo).convert("RGBA")
        elif fallback_photo and os.path.isfile(fallback_photo):
            avatar_source = Image.open(fallback_photo).convert("RGBA")
        avatar = add_round_corners(fit_image(avatar_source, (96, 96)), 24)
        canvas.alpha_composite(avatar, (INFO_RECT[0] + 18, INFO_RECT[1] + 16))

        draw = ImageDraw.Draw(canvas)
        title_font = load_font("font2.ttf", 46)
        meta_font = load_font("font.ttf", 25)
        small_font = load_font("font.ttf", 22)
        chip_font = load_font("font.ttf", 23)

        safe_title = truncate_text(draw, title, title_font, TITLE_AREA_WIDTH)
        safe_brand = truncate_text(draw, f"Powered By : {app.name}", meta_font, TITLE_AREA_WIDTH)
        safe_channel = truncate_text(draw, channel, small_font, 210)
        safe_views = truncate_text(draw, views, chip_font, 118)
        safe_duration = truncate_text(draw, duration, chip_font, 92)
        app_badge = truncate_text(draw, app.name, chip_font, 118)

        text_x = INFO_RECT[0] + 136
        draw.text((text_x, INFO_RECT[1] + 12), safe_title, fill="white", font=title_font)
        draw.text((text_x, INFO_RECT[1] + 62), safe_brand, fill=(236, 236, 236), font=meta_font)
        draw.text(
            (text_x, INFO_RECT[1] + 96),
            f"{safe_channel}  |  {safe_duration}",
            fill=(219, 219, 219),
            font=small_font,
        )

        draw.text(
            (brand_rect[0] + 16, brand_rect[1] + 10),
            app_badge,
            fill=(255, 255, 255),
            font=chip_font,
        )
        draw.text(
            (views_rect[0] + 18, views_rect[1] + 7),
            safe_views,
            fill=(255, 255, 255),
            font=chip_font,
        )
        draw.text(
            (duration_rect[0] + 18, duration_rect[1] + 8),
            safe_duration,
            fill=(255, 255, 255),
            font=chip_font,
        )
        try:
            os.remove(raw_thumb_path)
        except:
            pass
        canvas.convert("RGB").save(final_path, quality=95)
        return final_path
    except Exception:
        if os.path.isfile(raw_thumb_path):
            return raw_thumb_path
        return thumbnail
