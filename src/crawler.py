import aiohttp
import asyncio
from asyncio import Semaphore
import itertools
import config
import parser
from tenacity import retry,stop_after_attempt,retry_if_exception_type, wait_exponential
import seed_urls
from aiohttp_socks import ProxyConnector
from proxy import PROXY_POOL
import logging
import os
# 限制并发量，避免一次性开太多请求
CONCURRENT_REQUESTS = config.CONCURRENT_REQUESTS
headers = config.headers #请求头设置
#页面链接
links = config.links
base_url = config.base_url

#日志配置
LOG_DIR = "../log"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "crawler.log") #文件路径

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    '''控制台输出'''
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    '''文件输出,每次运行覆盖原日志'''
    file_handler = logging.FileHandler(LOG_FILE,mode="w",encoding="utf-8")
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    # 添加到 logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

#连接器管理器：为每个连接器配置代理
class ProxyManager:

    def __init__(self,proxy_pool):
        self.proxy_pool = proxy_pool #代理池
        self.connectors = []  # 存储配置了代理的连接器
        self.sessions = []  # 存储使用这些连接器的会话
        self.current_index = 0 #轮询代理会话
        self.initialized = False #标记连接器是否已经初始化过

    async def init_connectors(self):
        """ 为代理池中的每个代理创建专用的连接器 """
        if self.initialized:
            return

        logger.info(f"正在创建 {len(self.proxy_pool)} 个配置了代理的连接器...")

        for proxy_url in self.proxy_pool:
            try:
                """ 创建连接器并配置代理 """
                connector = ProxyConnector.from_url(
                    proxy_url,  # 这里配置代理
                    limit=5,  # 连接池大小
                    limit_per_host=6,  # 每个主机限制
                    keepalive_timeout=30,
                )

                # 创建使用该连接器的会话
                session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=config.timeout,
                    headers=headers,

                )

                self.connectors.append(connector)
                self.sessions.append(session)
                logger.info(f"✓ 创建连接器并配置代理: {proxy_url}")

            except Exception as e:
                logger.warning(f"✗ 创建代理连接器失败 {proxy_url}: {e}")
                continue

        # 如果没有代理，创建直连连接器
        if not self.connectors:
            logger.warning("没有可用代理，创建直连连接器")
            connector = aiohttp.TCPConnector(limit=28)
            session = aiohttp.ClientSession(
                connector=connector,
                timeout=config.timeout,
                headers=headers
            )
            self.connectors.append(connector)
            self.sessions.append(session)

        self.initialized = True
        logger.info(f"连接器初始化完成，共有 {len(self.connectors)} 个连接器")

    def get_session(self):
        """轮询返回配置了不同代理的会话"""
        if not self.sessions:
            return None

        session = self.sessions[self.current_index % len(self.sessions)]
        self.current_index += 1

        # 获取当前会话对应的代理信息（用于日志）
        proxy_index = (self.current_index - 1) % len(self.sessions)
        current_proxy = self.proxy_pool[proxy_index] if proxy_index < len(self.proxy_pool) else "直连"

        return session,current_proxy

    def get_connector_count(self):
        """返回连接器数量"""
        return len(self.connectors)

    def get_proxy_info(self,index):
        """获取指定连接器配置的代理信息"""
        if index < len(self.proxy_pool):
            return self.proxy_pool[index]
        return "直连"

    async def close_all(self):
        """关闭所有连接器和会话"""
        logger.info("正在关闭所有连接器和会话...")

        for i,session in enumerate(self.sessions):
            try:
                await session.close()
                proxy_info = self.get_proxy_info(i)
                logger.info(f"✓ 已关闭代理会话: {proxy_info}")
            except Exception as e:
                logger.warning(f"✗ 关闭会话时出错: {e}")

        for i,connector in enumerate(self.connectors):
            try:
                await connector.close()
                proxy_info = self.get_proxy_info(i)
                logger.info(f"✓ 已关闭连接器: {proxy_info}")
            except Exception as e:
                logger.warning(f"✗ 关闭连接器时出错: {e}")


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),  # 指数退避
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
)
async def scrape_book_details(book_url,sem,proxy_manager):
    """爬取图书详情 - 使用配置了代理的连接器"""
    async with sem:
        session_info = proxy_manager.get_session()
        if not session_info:
            logger.warning(f"✗ 没有可用的会话，跳过 {book_url}")
            return None

        session,current_proxy = session_info

        try:
            async with session.get(book_url) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    book_data = parser.parse_book_detail(html)
                    logger.info(f"✓ [{current_proxy}] 成功获取: {book_data['title'][:30]}...")
                    return book_data
                else:
                    logger.warning(f"✗ [{current_proxy}] 请求失败 {book_url}, 状态码: {resp.status}")
                    return None
        except Exception as e:
            logger.warning(f"✗ [{current_proxy}] 请求错误 {book_url}: {e}")
            return None


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),  # 指数退避
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
)
async def fetch_book_urls(url,sem,proxy_manager):
    """获取图书列表页链接 - 使用配置了代理的连接器"""
    async with sem:
        session_info = proxy_manager.get_session()
        if not session_info:
            logger.warning(f"✗ 没有可用的会话，跳过 {url}")
            return []

        session,current_proxy = session_info

        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    book_urls = parser.parse_book_href(html,base_url)
                    logger.info(f"✓ [{current_proxy}] 成功解析页面 {url}, 找到 {len(book_urls)} 个图书链接")
                    return book_urls
                else:
                    logger.warning(f"✗ [{current_proxy}] 页面请求失败 {url}, 状态码: {resp.status}")
                    return []
        except Exception as e:
            logger.warning(f"✗ [{current_proxy}] 页面请求错误 {url}: {e}")
            return []


async def main():
    # 创建连接器管理器
    proxy_manager = ProxyManager(PROXY_POOL)
    await proxy_manager.init_connectors()

    try:
        # 获取所有列表页URL
        urls = seed_urls.generate_page_urls()
        logger.info(f"共有 {len(urls)} 个列表页需要爬取")
        logger.info(f"创建了 {proxy_manager.get_connector_count()} 个配置了代理的连接器")

        # 设置并发信号量
        sem = Semaphore(CONCURRENT_REQUESTS)

        #获取所有图书详情页链接
        logger.info("开始获取图书链接...")
        book_tasks = [fetch_book_urls(url,sem,proxy_manager) for url in urls]
        book_urls_results = await asyncio.gather(*book_tasks)

        valid_urls = [urls for urls in book_urls_results if urls] #过滤空值
        flat_urls = list(itertools.chain.from_iterable(valid_urls)) #将二维数组转化为一维数组
        logger.info(f"共找到 {len(flat_urls)} 个图书详情页链接")

        #爬取图书详情
        logger.info("开始爬取图书详情...")
        detail_tasks = [scrape_book_details(url,sem,proxy_manager) for url in flat_urls]
        results = await asyncio.gather(*detail_tasks)


        valid_results = [r for r in results if r] # 过滤空值
        logger.info(f"成功获取 {len(valid_results)} 个图书详情")

        return valid_results

    finally:
        # 确保关闭所有连接器和会话
        await proxy_manager.close_all()


if __name__ == "__main__":
    asyncio.run(main())