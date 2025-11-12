# Books to Scrape 异步爬虫
作品集演示项目

一个高性能、可配置的异步网络爬虫，用于爬取 [Books to Scrape](http://books.toscrape.com/) 网站的图书数据。

## ✨ 特性亮点

### 🚀 高性能
- **异步并发**: 使用 `asyncio` 和 `aiohttp` 实现高并发请求
- **连接池管理**: 智能连接复用，减少 TCP 握手开销
- **信号量控制**: 精确控制并发数量，避免服务器压力

### 🛡️ 健壮性
- **智能重试机制**: 集成 `tenacity` 库，指数退避重试策略
- **代理池支持**: 自动轮询多个代理 IP，防止 IP 封禁
- **超时控制**: 多层超时设置，避免请求阻塞
- **全面异常处理**: 优雅处理各种网络异常情况

### 📊 可观测性
- **结构化日志**: 文件和控制台双输出，支持日志级别控制
- **进度监控**: 实时显示爬取进度和成功率
- **详细统计**: 爬取结果统计和错误报告

## 🚀 快速开始

### 环境要求
- Python 3.8+
- pip 包管理器

### 安装步骤

1. **克隆项目**
git clone https://github.com/RevolutionTTT/intern-portfolio.git
cd intern-portfolio
2. **创建虚拟环境**
bash

python -m venv venv

Windows
venv\Scripts\activate

Linux/Mac
source venv/bin/activate

复制
3. **安装依赖**
bash

pip install -r requirements.txt

复制
4. **运行爬虫**
bash

python main.py
