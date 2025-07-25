import time
import csv
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains

# ---------- 默认配置（可通过 CLI 覆盖） ----------
DEFAULT_QQ_ACCOUNT = ''      # 登录 QQ 账号
DEFAULT_QQ_PASSWORD = ''   # 登录 QQ 密码
DEFAULT_TARGET_UIN = ''      # 目标 QQ 空间 UIN
CHROME_DRIVER = r'D:\chromedriver-win64\chromedriver-win64\chromedriver.exe'  # ChromeDriver 路径
DEFAULT_CHROME_PATH = None     # Chrome 浏览器执行文件路径，若空则自动查找

# ---------- Selenium 驱动初始化 ----------
def init_driver(chrome_binary_path=None, headless=False):
    options = webdriver.ChromeOptions()
    if chrome_binary_path:
        options.binary_location = chrome_binary_path
    options.add_argument('--start-maximized')
    if headless:
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
    service = ChromeService(CHROME_DRIVER)
    return webdriver.Chrome(service=service, options=options)

# ---------- 登录函数 ----------
def login_qzone(driver, qq_account, qq_password):
    print("[INFO] 打开 QQ 登录页")
    driver.get('https://i.qq.com/')
    WebDriverWait(driver, 20).until(
        EC.frame_to_be_available_and_switch_to_it((By.ID, 'login_frame'))
    )
    print("[INFO] 切换为帐号密码登录")
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, 'switcher_plogin'))
    ).click()
    print("[INFO] 输入账号")
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, 'u'))
    ).send_keys(qq_account)
    print("[INFO] 输入密码")
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, 'p'))
    ).send_keys(qq_password)
    print("[INFO] 点击登录")
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, 'login_button'))
    ).click()
    print("[INFO] 登录中，等待跳转...")
    time.sleep(10)
    driver.switch_to.default_content()

# ---------- 爬取函数 ----------
def fetch_main_shuoshuo(driver, target_uin):
    driver.get(f'https://user.qzone.qq.com/{target_uin}/main')
    time.sleep(5)
    WebDriverWait(driver, 10).until(
        EC.frame_to_be_available_and_switch_to_it((By.ID, 'QM_Feeds_Iframe'))
    )
    print("[INFO] 已进入 QM_Feeds_Iframe")
    all_data = []
    last_count = -1
    unchanged_times = 0
    scroll_try = 0
    max_scroll_try = 100
    max_unchanged = 5
    while scroll_try < max_scroll_try:
        shuoshuos = driver.find_elements(By.CSS_SELECTOR, 'li.f-single.f-s-s')
        print(f"[INFO] 当前已加载说说数: {len(shuoshuos)}")
        if len(shuoshuos) == last_count:
            unchanged_times += 1
            print(f"[INFO] 说说数量未增加，累计未变次数: {unchanged_times}")
            if unchanged_times >= max_unchanged:
                print("[INFO] 连续多次未加载新说说，停止下拉。")
                break
        else:
            unchanged_times = 0
        last_count = len(shuoshuos)
        # 1. 直接将 feeds 容器 scrollTop 设置为最大
        driver.execute_script("var feeds=document.querySelector('.host_home_feeds');if(feeds&&feeds.parentElement){feeds.parentElement.scrollTop=999999;}")
        # 2. 直接将 body scrollTop 设置为最大
        driver.execute_script("document.body.scrollTop=999999;")
        # 3. window 滚动到底部
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        # 4. 模拟按下 End 键
        try:
            ActionChains(driver).send_keys(Keys.END).perform()
        except Exception as e:
            print('[WARN] 发送End键失败:', e)
        time.sleep(2)
        scroll_try += 1
    # 解析所有说说
    for s in driver.find_elements(By.CSS_SELECTOR, 'li.f-single.f-s-s'):
        try:
            try:
                content = s.find_element(By.CSS_SELECTOR, 'div.f-single-content.f-wrap div.f-info').text.strip()
            except:
                content = ''
            try:
                time_text = s.find_element(By.CSS_SELECTOR, 'div.info-detail > span.ui-mr8.state').text.strip()
            except:
                time_text = ''
            imgs = []
            try:
                img_elements = s.find_elements(By.CSS_SELECTOR, 'div.img-box img')
                for img in img_elements:
                    img_url = img.get_attribute('src')
                    if img_url and 'qlogo' not in img_url:
                        imgs.append(img_url)
            except:
                pass
            all_data.append([time_text, content, '|'.join(imgs)])
        except Exception as e:
            print('解析说说失败:', e)
    driver.switch_to.default_content()
    return all_data

# ---------- 保存函数 ----------
def save_to_csv(data, filename='shuoshuo.csv'):
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time', 'content', 'images'])
        writer.writerows(data)
    print(f'[INFO] 已保存 {len(data)} 条说说到 {filename}')

# ---------- CLI 参数解析 ----------
def parse_args():
    parser = argparse.ArgumentParser(description='QQ空间说说爬取')
    parser.add_argument('--account', type=str, default=DEFAULT_QQ_ACCOUNT, help='登录 QQ 账号')
    parser.add_argument('--password', type=str, default=DEFAULT_QQ_PASSWORD, help='登录 QQ 密码')
    parser.add_argument('--target', type=str, default=DEFAULT_TARGET_UIN, help='目标 QQ 号')
    parser.add_argument('--chrome-path', type=str, default=DEFAULT_CHROME_PATH, help='Chrome 可执行路径')
    parser.add_argument('--headless', action='store_true', help='是否无头模式')
    return parser.parse_args()

# ---------- 主流程 ----------
def main():
    args = parse_args()
    if not (args.account and args.password and args.target):
        print('请通过 --account, --password, --target 提供参数，或修改脚本默认值')
        return
    driver = init_driver(chrome_binary_path=args.chrome_path, headless=args.headless)
    try:
        login_qzone(driver, args.account, args.password)
        result = fetch_main_shuoshuo(driver, args.target)
        save_to_csv(result, filename=f"{args.target}.csv")
    except Exception as e:
        print('[ERROR] 发生错误:', e)
    finally:
        driver.quit()

if __name__ == '__main__':
    main()
