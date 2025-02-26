from pyppeteer import launch
import asyncio
import aiohttp
import os
import pandas as pd
import random
from datetime import datetime

import re


def extract_numeric_price(price_str):
    # 仅保留数字和小数点
    numeric_price = re.sub(r"[^\d.]", "", price_str)
    return numeric_price


current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

os.makedirs("product_images", exist_ok=True)
imgs = []
product_list = []


async def download_image(session, url, filename):
    async with session.get(url) as response:
        if response.status == 200:
            with open(filename, "wb") as file:
                file.write(await response.read())
            print(f"Downloaded: {filename}")
        else:
            print(f"Failed to download: {url}")


async def download_all_images(search_query, image_urls):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for index, url in enumerate(image_urls):
            file_name = f"product_images/{search_query}_{index + 1}.jpg"
            tasks.append(download_image(session, url, file_name))
        await asyncio.gather(*tasks)


async def fetch_aldi_data_pyppeteer(search_query, category):
    url = f"https://groceries.morrisons.com/search?q={search_query}"  # &sortBy=pricePerDescending

    browser = await launch(headless=True)  # 让浏览器可见，方便调试
    page = await browser.newPage()

    # 设置 User-Agent，模拟真实浏览器
    await page.setUserAgent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    await page.goto(url, {"waitUntil": "domcontentloaded"})  # 访问Aldi官网
    await page.waitForSelector('#onetrust-accept-btn-handler')
    await page.click('#onetrust-accept-btn-handler')
    await page.waitForSelector("#search")  # 确保搜索框加载完成

    print('加载完成')
    try:
        await page.waitForSelector(
            '#product-page > div > div._grid-item-12_tilop_45._grid-item-lg-10_tilop_273 > div > div.sc-6514kr-0.bZwGZy > div:nth-child(2) > div.product-card-container > div.header-container > a')
    except:
        print('1')
    # print(f"Search Results for '{search_query}':", products)

    # **查找所有搜索结果的产品链接**
    product_link_selector = "a[data-test='fop-product-link']"  # 你的 `a` 标签选择器
    await page.waitForSelector(product_link_selector)
    # **获取所有产品链接**
    product_links = await page.evaluate(
        """() => {
            return Array.from(document.querySelectorAll("a[data-test='fop-product-link']"))
                .map(a => a.href);
        }"""
    )

    # **去重并计数**
    product_links = list(set(product_links))
    print(f"Total products found: {len(product_links)}")

    useful_result = 0

    for link in product_links:
        # print(link)  # 打印所有产品链接
        if link != 'None':
            await page.goto(link)
            await page.waitForSelector(
                '#main > div > div:nth-child(3) > div > div.sc-mmemlz-0.bfMttO._box_107ii_1 > h1')
            product_title = await page.evaluate(
                """() => {
                    return document.querySelector("#main > div > div:nth-child(3) > div > div.sc-mmemlz-0.bfMttO._box_107ii_1 > h1").innerText;
                }""")
            product_price = await page.evaluate(
                """() => {
                    return document.querySelector("#main > div > div:nth-child(3) > div > div.sc-mmemlz-0.bfMttO._box_107ii_1 > div.sc-mmemlz-0.fjXwSW > span").innerText;
                }""")

            product_image_url = await page.evaluate(
                """() => {
                    let img = document.querySelector("#main > div > div:nth-child(2) > div > ul > li > button > img");  // 替换成你的 class 选择器
                    return img ? img.src : "No image found";
                }""")
            if product_image_url == "No image found":
                product_image_url = await page.evaluate(
                    """() => {
                        let img = document.querySelector("#main > div > div:nth-child(2) > div.sc-cvw5eh-0.gDapNg > ul > li:nth-child(2) > button > img");  // 替换成你的 class 选择器
                        return img ? img.src : "No image found";
                    }""")
            product_detail = await page.evaluate(
                """() => {
                    return document.querySelector("#main > div._grid_vea1m_1._grid--fixed_vea1m_28.salt-m-y--4 > div:nth-child(4) > div > div:nth-child(2) > div").innerText;
                }""")
            if product_image_url != 'No image found' and 'Morrisons' not in product_title and product_detail:
                # print(product_title)
                # print(product_price)
                # print(product_detail)
                # print(product_image_url.replace("/500x500",'/1280x1280'))
                useful_result += 1
                product_list.append({
                    "name": product_title,
                    "description": product_detail.replace('\n', ''),
                    "category": category,
                    "price": extract_numeric_price(product_price),
                    "stock": random.randint(1, 100),
                    "status": "active",
                    "picture": f'product_images/image_{useful_result}.jpg',  # 替换高清图
                    "created_time": current_time,
                    "updated_time": current_time,
                })
                imgs.append(product_image_url)
                print(useful_result)

    await download_all_images(search_query, imgs)
    df = pd.DataFrame(product_list)

    # **导出 CSV**
    df.to_csv(f"{search_query}.csv", index=False, encoding="utf-8")

    await browser.close()  # 关闭浏览器

    # return products  # 返回产品列表


# 运行代码
search_query = "milk"
category = 'food'

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    products = loop.run_until_complete(fetch_aldi_data_pyppeteer(search_query, category))
    print(products)
