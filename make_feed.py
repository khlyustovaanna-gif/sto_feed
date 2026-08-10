# -*- coding: utf-8 -*-
"""
Исправленный make_feed.py
- Всегда подставляет фиксированный description (USE_FIXED_DESCR = True)
- Гарантированно заполняет p["model"] и p["typePrefix"] перед выводом
- Всегда выводит теги <model> и <typePrefix> без условий
"""
import re
import html
import sys
import os

# --- Настройки ---
USE_FIXED_DESCR = True
FIXED_DESCR_TEXT = "Бесплатная техподдержка на весь срок. Доставка по РФ. Гарантия. Работаем с 2015г."

ВАЛЮТА = "RUB"
ОПИСАНИЕ_ПО_УМОЛЧАНИЮ = "Описание отсутствует"

id_of_name = {}
products = []


def html_escape(s):
    if s is None:
        return ""
    return html.escape(str(s), quote=True)


def normalize_url(u):
    if not u:
        return ""
    return u.strip()


def clean_text(s):
    if s is None:
        return ""
    t = re.sub(r"\s+", " ", s)
    return t.strip()


def extract_one(block):
    url = ""
    lm = re.search(r'class="js-product-link"\s+href="([^"]+)"', block)
    if not lm:
        lm = re.search(r'href="(/[^"]+)"', block)
    if lm:
        url = normalize_url(lm.group(1))

    image = ""
    im = re.search(r'itemprop="image"\s+content="([^"]+)"', block)
    if im:
        image = im.group(1)
    if not image:
        im = re.search(r'data-original="([^"]+)"', block)
        if im:
            image = im.group(1)
    image = normalize_url(image)

    title = ""
    tm = re.search(r'js-product-name"[^>]*>\s*(.*?)\s*</div>', block, re.DOTALL)
    if tm:
        title = clean_text(tm.group(1))
    if not title:
        return None

    # Заполняем descr заранее (будет заменён глобальным FIXED_DESCR_TEXT при генерации)
    descr = ОПИСАНИЕ_ПО_УМОЛЧАНИЮ

    price = ""
    pm = re.search(r'js-product-price[^>]*>\s*([^<]*)<', block, re.DOTALL)
    if pm:
        digits = re.sub(r"[^\d]", "", pm.group(1))
        if digits:
            price = digits
    if not price:
        return None

    # Попытки найти model/sku
    model = ""
    m = re.search(r'"sku"\s*:\s*"([^"]+)"', block, re.IGNORECASE)
    if not m:
        m = re.search(r'"sku"\s*:\s*\'([^\']+)\'', block, re.IGNORECASE)
    if not m:
        m = re.search(r'"mpn"\s*:\s*"([^"]+)"', block, re.IGNORECASE)
    if not m:
        m = re.search(r'itemprop=["\']sku["\']\s*content=["\']([^"\']+)["\']', block, re.IGNORECASE)
    if not m:
        m = re.search(r'data[-_]?(?:sku|article)=["\']([^"\']+)["\']', block, re.IGNORECASE)
    if not m:
        m = re.search(r'(?:Артикул|арт\.|article|SKU|sku)[:\s]*([A-Za-z0-9\-\_\/\s]+)', block, re.IGNORECASE)
    if m:
        model = m.group(1).strip()

    # fallback model: короткая версия title
    if not model and title:
        mv = re.sub(r"\s*\(.*\)\s*$", "", title)
        model = mv.strip()[:60]

    return {"title": title, "price": price, "descr": descr, "url": url, "image": image, "model": model}


def build_yml(products_list):
    out = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append('<yml_catalog date="2026-08-10 00:00">')
    out.append('  <shop>')
    out.append('    <name>My Shop</name>')
    out.append('    <company>My Company</company>')
    out.append('    <url>https://example.com</url>')
    out.append('    <currencies>')
    out.append(f'      <currency id="{ВАЛЮТА}" rate="1"/>')
    out.append('    </currencies>')
    out.append('    <categories>')
    out.append('    </categories>')
    out.append('    <offers>')

    for idx, p in enumerate(products_list, start=1):
        cid = id_of_name.get(p.get("category_name"), 0)
        out.append(f'      <offer id="{idx}" type="vendor.model" available="true">')
        if p.get("url"):
            out.append(f'        <url>{html_escape(p["url"])}</url>')
        out.append(f'        <price>{html_escape(p.get("price",""))}</price>')
        out.append(f'        <currencyId>{html_escape(ВАЛЮТА)}</currencyId>')
        out.append(f'        <categoryId>{html_escape(cid)}</categoryId>')
        if p.get("vendor"):
            out.append(f'        <vendor>{html_escape(p["vendor"])}</vendor>')

        # --- гарантия наличия model и typePrefix ---
        model_val = (p.get("model") or "").strip()
        if not model_val:
            mv = re.sub(r"\s*\(.*\)\s*$", "", p.get("title",""))
            model_val = (mv or "").strip()[:120]
        model_val = re.sub(r"[^0-9A-Za-zА-Яа-яёЁ \-_/]", "", model_val).strip()
        if not model_val:
            model_val = "no-model"
        p["model"] = model_val

        type_prefix = (p.get("typePrefix") or "").strip()
        if not type_prefix:
            type_prefix = (p.get("category_name") or "").strip()
        if not type_prefix and p.get("title"):
            type_prefix = p.get("title").split()[0]
        type_prefix = re.sub(r"[^0-9A-Za-zА-Яа-яёЁ \-_]", "", (type_prefix or "")).strip()[:50]
        if not type_prefix:
            type_prefix = "Товар"
        p["typePrefix"] = type_prefix

        # typePrefix and model (без условий)
        out.append(f'        <model>{html_escape(p["model"])}</model>')
        out.append(f'        <typePrefix>{html_escape(p["typePrefix"])}</typePrefix>')

        out.append(f'        <name>{html_escape(p.get("title",""))}</name>')
        if p.get("image"):
            out.append(f'        <picture>{html_escape(p["image"])}</picture>')

        # description: фиксированный текст при включённом флаге
        if USE_FIXED_DESCR:
            descr_text = FIXED_DESCR_TEXT
        else:
            descr_text = p.get("descr") or FIXED_DESCR_TEXT
        out.append(f'        <description>{html_escape(descr_text)}</description>')

        out.append('      </offer>')

    out.append('    </offers>')
    out.append('  </shop>')
    out.append('</yml_catalog>')
    return "\n".join(out)


def main():
    global products
    folder = "HTML_файлы"
    if not os.path.isdir(folder):
        print("Folder with HTML not found:", folder)
        return

    for fname in os.listdir(folder):
        if not fname.lower().endswith(".html"):
            continue
        # безопасное чтение: определяем кодировку и декодируем
        try:
            import chardet
            with open(os.path.join(folder, fname), "rb") as bf:
                b = bf.read()
            enc = chardet.detect(b).get("encoding") or "utf-8"
            txt = b.decode(enc, errors="replace")
        except Exception:
            # fallback: cp1251
            with open(os.path.join(folder, fname), encoding="cp1251", errors="replace") as f:
                txt = f.read()

        p = extract_one(txt)
        if p:
            p.setdefault("category_name", "Default")
            p.setdefault("vendor", "")
            p.setdefault("typePrefix", "")
            products.append(p)

    yml = build_yml(products)
    with open("feed.yml", "w", encoding="utf-8") as out:
        out.write(yml)
    print("feed.yml generated, offers:", len(products))


if __name__ == "__main__":
    main()
