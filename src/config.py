# 限制并发量，避免一次性开太多请求
import aiohttp
CONCURRENT_REQUESTS = 25
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}
links = ["https://books.toscrape.com/catalogue/category/books_1/index.html"]
base_url = "https://books.toscrape.com/catalogue/category/books_1/page-{}.html"
timeout = aiohttp.ClientTimeout(total=30,
                                sock_connect=10,  # socket连接超时
                                sock_read=10  # socket读取超时
                                )






