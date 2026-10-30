import asyncio
import io
import os
import sys
import time
from pathlib import Path
import httpx
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

ASSETS_DIR = Path(__file__).resolve().parent / "seed_assets"
PROD_DIR = ASSETS_DIR / "products"
MAKER_DIR = ASSETS_DIR / "makers"

PROD_DIR.mkdir(parents=True, exist_ok=True)
MAKER_DIR.mkdir(parents=True, exist_ok=True)

# Exact verified URLs from Wikimedia Commons
URL_MAP = {
    # Makers (7 artisans):
    # 0: Ramesh Kumar (Bhagalpur silk weaver)
    "m0": "https://upload.wikimedia.org/wikipedia/commons/2/23/Handloom_Weaver_in_an_exhibition_1.jpg",
    # 1: Sunita Devi (Woman weaver)
    "m1": "https://upload.wikimedia.org/wikipedia/commons/2/2b/A_young_artist_weaving_creativity_into_every_thread%2C_crafting_a_beautiful_handicraft_saree_with_precision_and_passion.jpg",
    # 2: Meena Jha (Senior Madhubani painter)
    "m2": "https://upload.wikimedia.org/wikipedia/commons/d/d8/Dilli_Haat_Madhubani_Mithila_Painting_Artist.jpg",
    # 3: Pooja Kumari (Young Madhubani painter)
    "m3": "https://upload.wikimedia.org/wikipedia/commons/0/03/Jadupatua_paintings_and_Madhubani_paintings.JPG",
    # 4: Kanta Ben (Hodka, senior Gujarati Kutch craftswoman)
    "m4": "https://upload.wikimedia.org/wikipedia/commons/5/5f/Karmi_Rabari.jpg",
    # 5: Ramila Ben (Bhujodi, Gujarati artisan)
    "m5": "https://upload.wikimedia.org/wikipedia/commons/b/b3/Eyes_of_Experience_-_Flickr_-_Meanest_Indian.jpg",
    # 6: Salim Qureshi (Master Khurja potter shaping clay on wheel)
    "m6": "https://upload.wikimedia.org/wikipedia/commons/c/cb/Potter_shaping_clay_on_a_traditional_manual_potter%EF%BF%BDs_wheel_in_India_01.jpg",

    # Products (21 listings, 2 photos each):
    # 0: Indigo cotton handloom saree
    "p0_0": "https://upload.wikimedia.org/wikipedia/commons/f/f6/Kasargod_saree_01.jpg",
    "p0_1": "https://upload.wikimedia.org/wikipedia/commons/8/80/Saree_Weaving_by_Handloom.jpg",

    # 1: Bhagalpuri Tussar silk saree
    "p1_0": "https://upload.wikimedia.org/wikipedia/commons/5/5b/Tussore_Sarees_-_Phulia_2016-11-12_1891.JPG",
    "p1_1": "https://upload.wikimedia.org/wikipedia/commons/4/40/Tussore_Sarees_-_Phulia_2016-11-12_1893.JPG",

    # 2: Red & white cotton handloom saree
    "p2_0": "https://upload.wikimedia.org/wikipedia/commons/4/40/Customers_Selecting_Tussore_Sarees_-_2_Natun_Phulia_-_Nadia_2016-11-12_1887.JPG",
    "p2_1": "https://upload.wikimedia.org/wikipedia/commons/0/0d/Customers_Selecting_Tussore_Sarees_-_2_Natun_Phulia_-_Nadia_2016-11-12_1888.JPG",

    # 3: Tussar silk stole / dupatta
    "p3_0": "https://upload.wikimedia.org/wikipedia/commons/b/bd/Customers_Selecting_Tussore_Sarees_-_2_Natun_Phulia_-_Nadia_2016-11-12_1902.JPG",
    "p3_1": "https://upload.wikimedia.org/wikipedia/commons/a/a3/Customers_Selecting_Tussore_Sarees_-_2_Natun_Phulia_-_Nadia_2016-11-12_1904.JPG",

    # 4: Indigo cotton handloom dupatta
    "p4_0": "https://upload.wikimedia.org/wikipedia/commons/c/c5/Blue_khadi_kurta.jpg",
    "p4_1": "https://upload.wikimedia.org/wikipedia/commons/f/f6/Kasargod_saree_01.jpg",

    # 5: Yellow & green cotton saree
    "p5_0": "https://upload.wikimedia.org/wikipedia/commons/a/ac/Customers_Selecting_Tussore_Sarees_-_2_Natun_Phulia_-_Nadia_2016-11-12_1886.JPG",
    "p5_1": "https://upload.wikimedia.org/wikipedia/commons/f/f1/A_man_weaving_the_famous_handloom_Chanderi_Saree.jpg",

    # 6: Handloom cotton kurta fabric yardage
    "p6_0": "https://upload.wikimedia.org/wikipedia/commons/f/f9/Khadi_Weaving_at_Ponduru_01.JPG",
    "p6_1": "https://upload.wikimedia.org/wikipedia/commons/8/80/Saree_Weaving_by_Handloom_2.jpg",

    # 7: Madhubani painting - Fish & Lotus
    "p7_0": "https://upload.wikimedia.org/wikipedia/commons/5/51/Madhubani_painting_by_Bhuvana_Meenakshi.jpg",
    "p7_1": "https://upload.wikimedia.org/wikipedia/commons/5/54/Madhubani_painiting.jpg",

    # 8: Madhubani painting - Tree of Life & birds
    "p8_0": "https://upload.wikimedia.org/wikipedia/commons/4/47/Madhubani_paintings_or_Milithila_Painting-IMG_0103.jpg",
    "p8_1": "https://upload.wikimedia.org/wikipedia/commons/a/a2/Madhubani_Painting_Exhibition.jpg",

    # 9: Madhubani painting - Sun God
    "p9_0": "https://upload.wikimedia.org/wikipedia/commons/0/03/Jadupatua_paintings_and_Madhubani_paintings.JPG",
    "p9_1": "https://upload.wikimedia.org/wikipedia/commons/8/8a/Madhubani_paintings_or_Milithila_Painting_-IMG_0028.jpg",

    # 10: Madhubani painting - Elephant
    "p10_0": "https://upload.wikimedia.org/wikipedia/commons/e/ec/Madhubani_art.jpg",
    "p10_1": "https://upload.wikimedia.org/wikipedia/commons/0/0d/Stamp_of_India_-_2000_-_Colnect_307681_-_Madhubani_Mithila_Paintings_-_se_tenant_pair.jpeg",

    # 11: Handcrafted Canvas Artwork (Peacock / Folk painting & user's cat canvas art)
    "p11_0": "https://upload.wikimedia.org/wikipedia/commons/7/70/Madhubani_Painting_2.jpg",
    "p11_1": "https://upload.wikimedia.org/wikipedia/commons/0/0b/PAINTING_OF_RADHA_KRISHNA.jpg",

    # 12: Kutch dupatta red/black mirror work
    "p12_0": "https://upload.wikimedia.org/wikipedia/commons/5/57/Antique_Kutch_Embroidery.jpg",
    "p12_1": "https://upload.wikimedia.org/wikipedia/commons/c/c4/Ahir_Embroidery_From_Kutch.jpg",

    # 13: Kutch cushion cover red/orange mirror work
    "p13_0": "https://upload.wikimedia.org/wikipedia/commons/c/c4/Ahir_Embroidery_From_Kutch.jpg",
    "p13_1": "https://upload.wikimedia.org/wikipedia/commons/5/57/Antique_Kutch_Embroidery.jpg",

    # 14: Kutch Toran wall hanging with mirrors
    "p14_0": "https://upload.wikimedia.org/wikipedia/commons/3/3a/Alter_Cloth_%28Toran%29%2C_Saurashtra%2C_Gujarat%2C_India%2C_20th_Century%2C_cotton%2C_metal_and_mirror_pieces._plain_weave_with_embroidery_and_mirror_work%2C_Honolulu_Academy_of_Arts.jpg",
    "p14_1": "https://upload.wikimedia.org/wikipedia/commons/c/ca/Vintage_Rabari_Bag_Wovensouls_Collection.jpg",

    # 15: Kutch blue/white stole mirror work
    "p15_0": "https://upload.wikimedia.org/wikipedia/commons/9/95/Shawl_from_India%2C_Rabari_culture%2C_Honolulu_Museum_of_Art_6794.1.JPG",
    "p15_1": "https://upload.wikimedia.org/wikipedia/commons/c/ca/Vintage_Rabari_Bag_Wovensouls_Collection.jpg",

    # 16: Kutch cushion cover mirror work
    "p16_0": "https://upload.wikimedia.org/wikipedia/commons/c/ca/Vintage_Rabari_Bag_Wovensouls_Collection.jpg",
    "p16_1": "https://upload.wikimedia.org/wikipedia/commons/3/3a/Alter_Cloth_%28Toran%29%2C_Saurashtra%2C_Gujarat%2C_India%2C_20th_Century%2C_cotton%2C_metal_and_mirror_pieces._plain_weave_with_embroidery_and_mirror_work%2C_Honolulu_Academy_of_Arts.jpg",

    # 17: Terracotta pot blue glaze
    "p17_0": "https://upload.wikimedia.org/wikipedia/commons/a/a8/Khurja_Pottery.jpg",
    "p17_1": "https://upload.wikimedia.org/wikipedia/commons/c/c1/Khurja_pottery_2.jpg",

    # 18: Pottery vase blue/brown
    "p18_0": "https://upload.wikimedia.org/wikipedia/commons/a/aa/Pottery_shop_Khurja_%282023%29.jpg",
    "p18_1": "https://upload.wikimedia.org/wikipedia/commons/1/18/Khurja_pottery_3.jpg",

    # 19: Set of wheel-thrown clay diya
    "p19_0": "https://upload.wikimedia.org/wikipedia/commons/2/26/Diwali_Diya_2.jpg",
    "p19_1": "https://upload.wikimedia.org/wikipedia/commons/5/5c/Diwali_Diya_3.jpg",

    # 20: Wheel-thrown terracotta planter
    "p20_0": "https://upload.wikimedia.org/wikipedia/commons/5/5a/Clay_pot_India_Tamil_word_7.3.JPG",
    "p20_1": "https://upload.wikimedia.org/wikipedia/commons/a/a3/Clay_pot_India_Tamil_word_7.jpg",
}


def crop_to_aspect(img: Image.Image, target_w: int = 1000, target_h: int = 1250, is_detail: bool = False) -> Image.Image:
    """Crop image to exactly 4:5 ratio. If is_detail, crop a tighter center region."""
    img = img.convert("RGB")
    src_w, src_h = img.size

    if is_detail:
        crop_w = int(src_w * 0.65)
        crop_h = int(src_h * 0.65)
        left = (src_w - crop_w) // 2
        top = (src_h - crop_h) // 2
        img = img.crop((left, top, left + crop_w, top + crop_h))
        src_w, src_h = img.size

    target_aspect = target_w / target_h
    src_aspect = src_w / src_h

    if src_aspect > target_aspect:
        new_w = int(src_h * target_aspect)
        offset = (src_w - new_w) // 2
        img = img.crop((offset, 0, offset + new_w, src_h))
    else:
        new_h = int(src_w / target_aspect)
        offset = (src_h - new_h) // 2
        img = img.crop((0, offset, src_w, offset + new_h))

    return img.resize((target_w, target_h), Image.Resampling.LANCZOS)


async def download_item(client: httpx.AsyncClient, sem: asyncio.Semaphore, key: str, url: str):
    is_maker = key.startswith("m")
    dest = (MAKER_DIR if is_maker else PROD_DIR) / f"{key}.jpg"

    if dest.exists() and dest.stat().st_size > 10000:
        print(f"  [cached] {key} -> {dest.name}")
        return

    async with sem:
        for attempt in range(4):
            try:
                await asyncio.sleep(0.4)
                r = await client.get(url, timeout=25.0)
                if r.status_code == 200:
                    raw = Image.open(io.BytesIO(r.content))
                    is_detail = key.endswith("_1")
                    processed = crop_to_aspect(raw, 1000, 1250, is_detail=is_detail)
                    processed.save(dest, "JPEG", quality=92, optimize=True)
                    print(f"  [saved] {key} ({raw.size} -> 1000x1250) -> {dest.name}")
                    return
                elif r.status_code == 429:
                    wait_s = 2.0 * (attempt + 1)
                    print(f"  [429 rate limit] {key}, backing off {wait_s}s...")
                    await asyncio.sleep(wait_s)
                else:
                    print(f"  [http {r.status_code}] {key}")
                    break
            except Exception as e:
                print(f"  [err] {key} attempt {attempt}: {e}")
                await asyncio.sleep(1.0)


async def main():
    print(f"Starting polite download of {len(URL_MAP)} authentic craft assets...")
    sem = asyncio.Semaphore(1)
    headers = {"User-Agent": "KaruArtisanPlatform/2.0 (crafts@karu.test; educational research)"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        for k, u in URL_MAP.items():
            await download_item(client, sem, k, u)

    cat_upload = Path(r"C:\Users\pc\.gemini\antigravity\brain\37ee5b82-f98a-4625-a2e5-be2ff316b463\.user_uploaded\media_1792885248598_ce3b5af7.png")
    if cat_upload.exists():
        raw = Image.open(cat_upload).convert("RGB")
        cat_processed = crop_to_aspect(raw, 1000, 1250)
        cat_dest = PROD_DIR / "cat_craft.jpg"
        cat_processed.save(cat_dest, "JPEG", quality=92)
        print(f"  [saved] user uploaded cat painting -> {cat_dest.name}")

    prod_files = list(PROD_DIR.glob("*.jpg"))
    maker_files = list(MAKER_DIR.glob("*.jpg"))
    print(f"\nVerification:")
    print(f"  Product photos saved: {len(prod_files)} / 42")
    print(f"  Maker photos saved:   {len(maker_files)} / 7")


if __name__ == "__main__":
    asyncio.run(main())
