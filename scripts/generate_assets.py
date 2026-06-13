import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

repo = Path(__file__).resolve().parents[1]
asset_dir = repo / "docs/assets"
asset_dir.mkdir(parents=True, exist_ok=True)
hermes_src = Path("/root/clawd/repos/hermes-wt-supplog/website/static/img/logo.png")
hermes_logo_path = asset_dir / "hermes-logo.png"
shutil.copyfile(hermes_src, hermes_logo_path)

font_candidates = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]
font_path = next(p for p in font_candidates if Path(p).exists())
regular_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
mono_font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def make_logo(size: int) -> Image.Image:
    logo = Image.open(hermes_logo_path).convert("RGBA")
    xs = []
    ys = []
    for y in range(logo.height):
        for x in range(logo.width):
            r, g, b, a = logo.getpixel((x, y))
            if a > 0 and (r + g + b) / 3 < 245:
                xs.append(x)
                ys.append(y)
    left, top, right, bottom = min(xs), min(ys), max(xs) + 1, max(ys) + 1
    logo = logo.crop((left, top, right, bottom))
    logo.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    canvas.alpha_composite(logo, ((size - logo.width) // 2, (size - logo.height) // 2))
    return canvas


def draw_word_art(
    text: str, out_path: Path, width: int = 1600, height: int = 260
) -> None:
    img = Image.new("RGBA", (width, height), (2, 6, 23, 255))
    draw = ImageDraw.Draw(img)
    for x in range(0, width, 36):
        draw.line([(x, 0), (x + 180, height)], fill=(255, 139, 23, 18), width=1)
    for y in range(25, height, 34):
        draw.line([(0, y), (width, y)], fill=(255, 190, 20, 12), width=1)

    logo_size = 190
    left_pad = 55 + logo_size + 35
    right_pad = 45
    font_size = 112
    while font_size > 40:
        font = ImageFont.truetype(font_path, font_size)
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=3)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if tw <= width - left_pad - right_pad:
            break
        font_size -= 3
    font = ImageFont.truetype(font_path, font_size)
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=3)
    th = bbox[3] - bbox[1]
    x = left_pad
    y = (height - th) // 2 - 10

    for offset, col in [
        (13, (0, 0, 0, 210)),
        (10, (112, 72, 18, 210)),
        (7, (182, 99, 17, 220)),
        (4, (30, 30, 30, 230)),
    ]:
        draw.text(
            (x + offset, y + offset),
            text,
            font=font,
            fill=col,
            stroke_width=3,
            stroke_fill=(0, 0, 0, 230),
        )
    for dx, dy in [(6, 0), (0, 6), (-3, 3), (3, -3)]:
        draw.text(
            (x + dx, y + dy),
            text,
            font=font,
            fill=(12, 12, 12, 255),
            stroke_width=5,
            stroke_fill=(0, 0, 0, 255),
        )

    text_layer = Image.new("L", (width, height), 0)
    td = ImageDraw.Draw(text_layer)
    td.text((x, y), text, font=font, fill=255, stroke_width=2, stroke_fill=255)
    grad = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for yy in range(height):
        t = yy / height
        if t < 0.45:
            r = 255
            g = int(220 - 45 * t / 0.45)
            b = 0
        else:
            k = (t - 0.45) / 0.55
            r = int(255 - 98 * k)
            g = int(175 - 92 * k)
            b = int(15 * k)
        gd.line([(0, yy), (width, yy)], fill=(r, g, b, 255))
    img.alpha_composite(
        Image.composite(
            grad, Image.new("RGBA", (width, height), (0, 0, 0, 0)), text_layer
        )
    )
    draw.text(
        (x - 1, y - 2),
        text,
        font=font,
        fill=(255, 244, 117, 120),
        stroke_width=1,
        stroke_fill=(255, 244, 117, 70),
    )

    mark = make_logo(logo_size)
    cx, cy = 38, (height - logo_size) // 2
    glow = Image.new("RGBA", (logo_size + 34, logo_size + 34), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.rounded_rectangle(
        [7, 7, logo_size + 27, logo_size + 27], radius=30, fill=(255, 122, 16, 90)
    )
    glow = glow.filter(ImageFilter.GaussianBlur(12))
    img.alpha_composite(glow, (cx - 17, cy - 17))
    bg = Image.new("RGBA", (logo_size, logo_size), (255, 255, 255, 255))
    mask = Image.new("L", (logo_size, logo_size), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, logo_size, logo_size], radius=28, fill=255)
    img.paste(bg, (cx, cy), mask)
    img.alpha_composite(mark, (cx, cy))
    draw.rounded_rectangle(
        [cx, cy, cx + logo_size, cy + logo_size],
        radius=28,
        outline=(255, 159, 28, 255),
        width=4,
    )
    img.save(out_path)


def draw_infographic(out_path: Path, width: int = 1600, height: int = 900) -> None:
    img = Image.new("RGBA", (width, height), (3, 7, 18, 255))
    draw = ImageDraw.Draw(img)
    for r, alpha in [(700, 30), (500, 35), (320, 40)]:
        glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse(
            [width // 2 - r, height // 2 - r, width // 2 + r, height // 2 + r],
            fill=(255, 111, 25, alpha),
        )
        glow = glow.filter(ImageFilter.GaussianBlur(90))
        img.alpha_composite(glow)
    title_font = ImageFont.truetype(font_path, 80)
    body_font = ImageFont.truetype(regular_font, 31)
    small_font = ImageFont.truetype(regular_font, 24)
    mono_font = ImageFont.truetype(mono_font_path, 28)

    title = "HERMES BRAVE SEARCH PRO"
    bbox = draw.textbbox((0, 0), title, font=title_font, stroke_width=2)
    tx = (width - (bbox[2] - bbox[0])) // 2
    ty = 40
    for off, col in [(7, (0, 0, 0, 220)), (4, (158, 80, 12, 220))]:
        draw.text(
            (tx + off, ty + off),
            title,
            font=title_font,
            fill=col,
            stroke_width=2,
            stroke_fill=(0, 0, 0, 220),
        )
    draw.text(
        (tx, ty),
        title,
        font=title_font,
        fill=(255, 196, 0, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255),
    )

    logo = make_logo(250)
    lx, ly = (width - 250) // 2, 200
    card = [lx - 25, ly - 25, lx + 275, ly + 275]
    draw.rounded_rectangle(
        card, radius=42, fill=(255, 255, 255, 255), outline=(255, 126, 25, 255), width=5
    )
    img.alpha_composite(logo, (lx, ly))
    draw.text(
        (width // 2 - 120, ly + 305),
        "Hermes Agent",
        font=body_font,
        fill=(235, 241, 255, 255),
    )

    cards = [
        ("web_search", "brave-pro", "Default discovery backend", 90, 545),
        ("brave_search", "advanced modes", "Images, news, videos, raw", 610, 545),
        ("web_extract", "tavily", "Extraction stays separate", 1130, 545),
    ]
    for h, sub, desc, x, y in cards:
        draw.rounded_rectangle(
            [x, y, x + 380, y + 205],
            radius=28,
            fill=(10, 18, 35, 245),
            outline=(255, 126, 25, 230),
            width=3,
        )
        draw.text((x + 30, y + 28), h, font=mono_font, fill=(255, 196, 0, 255))
        draw.text((x + 30, y + 78), sub, font=body_font, fill=(255, 255, 255, 255))
        draw.text((x + 30, y + 128), desc, font=small_font, fill=(169, 184, 208, 255))
        draw.line(
            [(width // 2, ly + 275), (x + 190, y)], fill=(255, 126, 25, 160), width=4
        )

    strip = [260, 790, 1340, 855]
    draw.rounded_rectangle(
        strip, radius=18, fill=(0, 0, 0, 180), outline=(64, 90, 130, 180), width=2
    )
    draw.text(
        (300, 807),
        'web.search_backend: "brave-pro"    web.extract_backend: "tavily"',
        font=mono_font,
        fill=(226, 236, 255, 255),
    )
    img.save(out_path)


draw_word_art(
    "HERMES BRAVE SEARCH PRO", asset_dir / "hermes-brave-search-pro-banner.png"
)
draw_infographic(asset_dir / "brave-hermes-hero.png")
print("created assets")
