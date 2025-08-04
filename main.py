import time
import csv
import argparse
import pymysql
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'shisannian1223',
    'database': 'student_analysis',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}



# ---------- 默认配置 ----------
DEFAULT_QQ_ACCOUNT = '3287424602'  # 登录 QQ 账号
DEFAULT_QQ_PASSWORD = 'shisannian1223'  # 登录 QQ 密码
CHROME_DRIVER = r'D:\\chromedriver-win64\\chromedriver-win64\\chromedriver.exe'  # ChromeDriver 路径
DEFAULT_CHROME_PATH = None  # Chrome 浏览器执行文件路径
DELAY_BETWEEN_TARGETS = 10  # 爬取不同目标账号之间的延迟（秒）
MAX_RETRIES = 3  # 每个目标的最大重试次数


# ---------- Selenium 驱动初始化 ----------
def init_driver(chrome_binary_path=None, headless=False):
    options = webdriver.ChromeOptions()
    if chrome_binary_path:
        options.binary_location = chrome_binary_path
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    if headless:
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')

    service = ChromeService(CHROME_DRIVER)
    driver = webdriver.Chrome(service=service, options=options)

    # 隐藏自动化特征
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


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

#---------- 从数据库获取QQ号 ----------
def get_qq_numbers_from_database():
    """从student表中获取所有QQ号(无限制)"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # 注意：根据实际表结构调整SQL语句
            cursor.execute("SELECT qq_id FROM students WHERE qq_id IS NOT NULL")
            result = cursor.fetchall()
            # 提取所有非空的qq_id
            qq_numbers = [str(row['qq_id']) for row in result if row['qq_id']]
            return qq_numbers
    except pymysql.Error as e:
        print(f'[ERROR] 从数据库获取QQ号失败: {e}')
        return []
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

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
def save_to_database(data, qq_id):
    """保存数据到MySQL数据库"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # 检查QQ号是否存在于Students表
            cursor.execute("SELECT id FROM Students WHERE qq_id = %s", (qq_id,))
            if not cursor.fetchone():
                # 如果不存在，则插入新记录
                cursor.execute("INSERT INTO Students (qq_id) VALUES (%s)", (qq_id,))
                connection.commit()
                print(f"[INFO] 已添加新QQ号到数据库: {qq_id}")

            # 插入说说数据
            sql = """
            INSERT INTO QQPosts (qq_id, post_at, content, images)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE content=VALUES(content), images=VALUES(images)
            """
            count = 0
            for item in data:
                time_text, content, images = item
                # 转换时间格式，这里需要根据实际时间格式调整
                try:
                    post_at = datetime.strptime(time_text, '%Y-%m-%d %H:%M')
                except:
                    post_at = datetime.now()  # 如果解析失败，使用当前时间
                
                cursor.execute(sql, (qq_id, post_at, content, images))
                count += 1
            
            connection.commit()
            print(f'[INFO] 已保存 {count} 条说说到数据库 (QQ: {qq_id})')
            return count
            
    except pymysql.Error as e:
        print(f'[ERROR] 数据库操作失败: {e}')
        # 如果数据库保存失败，回退到CSV保存
        print('[WARNING] 数据库保存失败，将尝试保存到CSV文件')
        return save_to_csv(data, f"{qq_id}_fallback.csv")
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()
'''
def save_to_csv(data, filename='shuoshuo.csv'):
    """保留CSV"""
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time', 'content', 'images'])
        writer.writerows(data)
    print(f'[INFO] 已保存 {len(data)} 条说说到 {filename}')
    return len(data)
'''



# ---------- 主流程 ----------
def main():
    args = parse_args()

    # 处理目标账号
    if args.target:
        # 如果通过命令行参数指定了目标QQ号
        targets = [t.strip() for t in args.target.split(',') if t.strip()]
    else:
        # 否则从数据库读取目标QQ号
        print('[INFO] 未指定目标QQ号，将从数据库读取...')
        targets = get_qq_numbers_from_database()
        if not targets:
            print('错误：未找到有效的QQ号，请检查数据库连接或使用 --target 参数')
            return
        print(f'[INFO] 从数据库读取到 {len(targets)} 个目标QQ号')

    print(f"[INFO] 准备爬取 {len(targets)} 个目标账号: {', '.join(targets)}")

    driver = init_driver(chrome_binary_path=args.chrome_path, headless=args.headless)

    try:
        login_qzone(driver, args.account, args.password)
        total_shuoshuo = 0

        # 循环处理每个目标账号
        for i, target_uin in enumerate(targets):
            print(f"\n[INFO] 开始处理目标 {i + 1}/{len(targets)}: {target_uin}")

            retries = 0
            data = []

            # 重试机制
            while retries < args.retries and not data:
                try:
                    data = fetch_main_shuoshuo(driver, target_uin)
                    if not data:
                        print(f"[WARNING] 未获取到数据，可能是访问受限或账号不存在")
                except Exception as e:
                    print(f"[ERROR] 爬取 {target_uin} 时出错: {e}")

                if not data:
                    retries += 1
                    if retries < args.retries:
                        print(f"[INFO] 将在 {args.delay} 秒后重试 ({retries}/{args.retries})")
                        time.sleep(args.delay)

            if data:
                # 保存到数据库
                count = save_to_database(data, target_uin)
                # 可选：同时保存一份CSV备份
                # save_to_csv(data, filename=f"{target_uin}.csv")
                total_shuoshuo += count
            else:
                print(f"[WARNING] 跳过目标账号 {target_uin}，未能获取数据")

            # 如果不是最后一个目标，添加延迟
            if i < len(targets) - 1:
                print(f"[INFO] 等待 {args.delay} 秒后处理下一个目标...")
                time.sleep(args.delay)

        print(f"\n[SUCCESS] 所有目标处理完成！共爬取 {len(targets)} 个账号，总计 {total_shuoshuo} 条说说")

    except Exception as e:
        print('[ERROR] 主流程发生错误:', e)
    finally:
        driver.quit()


if __name__ == '__main__':
    main()