from urllib.parse import urljoin
from lxml import etree

def parse_book_detail(html):
    tree = etree.HTML(html)
    title = tree.xpath('//div[@class="col-sm-6 product_main"]/h1/text()')
    price = tree.xpath('//div[@class="col-sm-6 product_main"]/p[@class="price_color"]/text()')
    description = tree.xpath('//div[@id="product_description"]/following-sibling::p/text()')
    title = title[0] if title else "未命名"
    price = price[0] if price else "未定价"
    description = description[0] if description else "无描述"
    book = {
        "title": title,
        "price": price,
        "description": description
    }
    return book
def parse_book_href(html, base_url):
    tree = etree.HTML(html)
    hrefs = tree.xpath('//article[@class="product_pod"]/h3/a/@href')
    print(hrefs)
    book_urls = [urljoin(base_url,href) for href in hrefs if href is not None]
    print(book_urls)
    return book_urls