import os

# config.py
QQ_NUMBER = '你的QQ号'
QQ_PASSWORD = '你的QQ密码'
CHROME_DRIVER = r'C:/path/to/chromedriver.exe'
DATA_DIR = 'data'
IMG_DIR = 'data/images'

# 浏览器配置
CHROME_OPTIONS = [
    '--headless',  # 无头模式
    '--disable-gpu',
    '--no-sandbox',
    '--disable-dev-shm-usage'
]

# 爬虫参数
POLL_INTERVAL = 300  # 轮询间隔(秒)
MAX_RETRY = 3  # 最大重试次数
TIMEOUT = 30  # 页面加载超时时间(秒)

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'