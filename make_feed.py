# -*- coding: utf-8 -*-
"""
make_feed.py — генератор YML фида.
Путь к источнику установлен на C:\feed\HTML_файлы
Скрипт ищет файлы с расширениями .txt, .html и .htm
"""

import os
import re
import glob
import datetime

# Настройки
САЙТ = "https://sto.cross-export.ru"
# Путь к папке с HTML-файлами разделов (вложенная папка HTML_файлы)
ИСТОЧНИК = r"C:\feed\HTML_файлы"
НАЗВАНИЕ_МАГАЗИНА = "КРОСС ЭКСПОРТ"
ВАЛЮТА = "RUB"
БРЕНД = "КРОСС ЭКСПОРТ"
ОПИСАНИЕ_ПО_УМОЛЧАНИЮ = "Бесплатная техподдержка на весь срок. Доставка по РФ. Гарантия. Работаем с 2015г."
БРАТЬ_ОПИСАНИЕ = False
КАТЕГОРИЯ_ПО_УМОЛЧАНИЮ = "Оборудование для ремонта ДВС"
СЛУЖЕБНЫЕ_КАТЕГОРИИ = (
    "404 page not found",
    "спасибо за заявку",
    "политика конфиденциальности",
    "header",
    "footer",
    "разделы каталога",
    "каталог оборудования",
)


def html_escape(s):
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


def clean_text(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&nbsp;|&#160;", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def normalize_url(raw):
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw.startswith("//"):
        return "https:" + raw
    if raw.startswith("http"):
        return raw
    if raw.startswith("/"):
        return САЙТ + raw
    return САЙТ + "/" + raw


def категория_из_title(html):
    m = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
    if not m:
        return КАТЕГОРИЯ_ПО_УМОЛЧАНИЮ
    t = clean_text(m.group(1))
    t = re.sub(r"\s*—\s*ООО\s*«[^»]*»\s*$", "", t)
    t = re.sub(r",\s*цена[^,]*$", "", t, flags=re.IGNORECASE)
    t = re.sub(r",\s*доставка[^,]*$", "", t, flags=re.IGNORECASE)
    return t.strip() or КАТЕГОРИЯ_ПО_УМОЛЧАНИЮ


def это_служебная(название):
    n = (название or "").lower().strip()
    for s in СЛУЖЕБНЫЕ_КАТЕГОРИИ:
        if n.startswith(s) or s in n:
            return True
    return False


def extract_products_from_html(html):
    products = []
    blocks = re.split(r'class="t778__col[^"]*?\bjs-product\b[^"]*"', html)
    for block in blocks[1:]:
        p = extract_one(block)
        if p:
            products.append(p)
    return products


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

    descr = ОПИСАНИЕ_ПО_УМОЛЧАНИЮ

    price = ""
    pm = re.search(r'js-product-price[^>]*>\s*([^<]*)<', block, re.DOTALL)
    if pm:
        digits = re.sub(r"[^\d]", "", pm.group(1))
        if digits:
            price = digits
    if not price:
        return None

    return {"title": title, "price": price, "descr": descr, "url": url, "image": image}


def build_yml(products):
    today = datetime.date.today().strftime("%Y-%m-%d %H:%M")
    cat_names = []
    for p in products:
        if p["category_name"] not in cat_names:
            cat_names.append(p["category_name"])
    id_of_name = {name: i + 1 for i, name in enumerate(cat_names)}

    out = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append('<!DOCTYPE yml_catalog SYSTEM "shops.dtd">')
    out.append('<yml_catalog date="%s">' % today)
    out.append('  <shop>')
    out.append('    <name>%s</name>' % html_escape(НАЗВАНИЕ_МАГАЗИНА))
    out.append('    <company>%s</company>' % html_escape(НАЗВАНИЕ_МАГАЗИНА))
    out.append('    <url>%s</url>' % html_escape(САЙТ))
    out.append('    <currencies>')
    out.append('      <currency id="%s" rate="1"/>' % ВАЛЮТА)
    out.append('    </currencies>')
    out.append('    <categories>')
    for i, name in enumerate(cat_names, start=1):
        out.append('      <category id="%s">%s</category>' % (i, html_escape(name)))
    out.append('    </categories>')
    out.append('    <offers>')

    for idx, p in enumerate(products, start=1):
        cid = id_of_name[p["category_name"]]
        out.append('      <offer id="%d" type="vendor.model" available="true">' % idx)
        if p["url"]:
            out.append('        <url>%s</url>' % html_escape(p["url"]))
        out.append('        <price>%s</price>' % p["price"])
        out.append('        <currencyId>%s</currencyId>' % ВАЛЮТА)
        out.append('        <categoryId>%s</categoryId>' % cid)
        if БРЕНД:
            out.append('        <vendor>%s</vendor>' % html_escape(БРЕНД))
        out.append('        <name>%s</name>' % html_escape(p["title"]))
        if p["image"]:
            out.append('        <picture>%s</picture>' % html_escape(p["image"]))
        if p["descr"]:
            out.append('        <description>%s</description>' % html_escape(p["descr"]))
        out.append('      </offer>')

    out.append('    </offers>')
    out.append('  </shop>')
    out.append('</yml_catalog>')
    return "\n".join(out)


def main():
    if not os.path.isdir(ИСТОЧНИК):
        print("Не найдена папка с HTML-файлами:", ИСТОЧНИК)
        print("Проверьте переменную ИСТОЧНИК в начале скрипта.")
        return

    files = []
    for ext in ("*.txt", "*.html", "*.htm"):
        files += glob.glob(os.path.join(ИСТОЧНИК, ext))
    files.sort()
    if not files:
        print("В папке не найдено HTML-файлов:", ИСТОЧНИК)
        return

    products = []
    print("%-42s %-52s %7s" % ("ФАЙЛ", "КАТЕГОРИЯ", "ТОВАРОВ"))
    print("-" * 110)
    for f in files:
        with open(f, "r", encoding="utf-8", errors="ignore") as fh:
            html = fh.read()
        cat_name = категория_из_title(html)
        found = extract_products_from_html(html)
        if это_служебная(cat_name):
            print("%-42s %-52s %7s" % (os.path.basename(f)[:42], "(служебная — пропущена)", 0))
            continue
        for p in found:
            p["category_name"] = cat_name
        products.extend(found)
        print("%-42s %-52s %7d" % (os.path.basename(f)[:42], cat_name[:52], len(found)))

    seen = set()
    unique = []
    for p in products:
        key = p["url"] or p["title"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)

    yml = build_yml(unique)
    with open(os.path.join(os.path.dirname(__file__), "feed.yml"), "w", encoding="utf-8") as fh:
        fh.write(yml)

    print("-" * 110)
    print("ГОТОВО! Товаров в фиде:", len(unique))
    cnt = {}
    for p in unique:
        cnt[p["category_name"]] = cnt.get(p["category_name"], 0) + 1
    print("Распределение по категориям:")
    for name in sorted(cnt.keys()):
        print("   %-62s: %d" % (name, cnt[name]))
    print("Файл feed.yml сохранён рядом со скриптом.")


if __name__ == "__main__":
    main()
