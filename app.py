from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import numpy as np
import subprocess
from selenium.webdriver.common.action_chains import ActionChains
import signal
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

gameboard = np.zeros((7, 6), dtype=int)  # 列优先，1到7列，行号在游戏里是上小下大,1到6行
# 0表示空，1表示红色，2表示黄色
driver = None  # 初始化 driver 为 None
last_suggestion: int 

# Define a flag to indicate whether the program should stop
stop_flag = False

def signal_handler(signum, frame):
    global stop_flag
    print("CTRL+D detected. Stopping the program...")
    stop_flag = True

signal.signal(signal.SIGINT, signal_handler)

def reset_gameboard():
    global gameboard
    gameboard = np.zeros((7, 6), dtype=int)  # 重置游戏棋盘

def open_browser():
    global driver
    if driver is None:  # 如果浏览器未启动，则启动
        driver = webdriver.Edge(keep_alive=True)
        driver.get('https://boardgamearena.com/')
        print("浏览器已启动并打开页面。")
    else:
        print("浏览器已启动，无需重复打开。")

def close_browser():
    global driver
    if driver is not None:  # 如果浏览器已启动，则关闭
        driver.quit()
        driver = None
        print("浏览器已关闭。")
    else:
        print("浏览器未启动，无需关闭。")

def login():
    global driver
    raise NotImplementedError("登录功能尚未实现。")


def update_gameboard():
    global gameboard
    reset_gameboard()  # 重置游戏棋盘
    global driver
    if driver is not None:  # 确保浏览器已启动
        try:
            for col in range(7):
                for row in range(6):
                    element_id = f"disc_{col+1}{row+1}"
                    try:
                        element = driver.find_element(By.ID, element_id)
                        element_class = element.get_attribute("class")
                        if "disccolor_ff0000" in element_class:
                            gameboard[col, row] = 1
                        elif "disccolor_ffff00" in element_class:
                            gameboard[col, row] = 2
                    except Exception:
                        # 如果元素不存在，跳过
                        continue
            print("游戏棋盘已更新：")
            print(gameboard.T)
            button = driver.find_element(By.XPATH, "/html/body/div[3]/div[1]/div[1]")
            button.click()
        except Exception as e:
            print(f"更新游戏棋盘失败: {e}")
    else:
        print("浏览器未启动，请先打开浏览器。")

def print_gameboard():
    global gameboard
    print("当前游戏棋盘：")
    for row in range(-1, 5, 1):
        line = ""
        for col in range(7):
            if gameboard[col, row] == 1:
                line += "X "
            elif gameboard[col, row] == 2:
                line += "O "
            else:
                line += "_ "
        print(line.strip())
    print("1 2 3 4 5 6 7")  # 打印列号

def query_external_program():
    global gameboard, last_suggestion
    pos = np.int64(0)  # Initialize pos as int64
    mask = np.int64(0)  # Initialize mask as int64
    moves = 0

    moves = np.sum(gameboard == 1) + np.sum(gameboard == 2)
    cur_player = 1 if moves % 2 == 0 else 2

    # Iterate through the gameboard to calculate pos and mask
    for col in range(7):
        for row in range(6):
            bit_position = col * 7 + (5 - row)  # Calculate bit position
            if gameboard[col, row] == cur_player:
                pos |= (np.int64(1) << bit_position)  # Set the bit for the current player's position
            if gameboard[col, row] != 0:
                mask |= (np.int64(1) << bit_position)  # Set the bit for any occupied position

    print(f"Player {cur_player}'s position (pos): {bin(pos)}")
    print(f"Mask of occupied positions (mask): {bin(mask)}")

    cmd = [
    "wsl",
    "/mnt/d/_work/connect-four-solver/a.out",
    "suggest",
    "-l", "/mnt/d/_work/connect-four-solver/table",
    "-t", "8",
    "-d", "8",
    "-bp", str(pos),
    "-bm", str(mask),
    "-bo", str(moves),
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    last_line = list(process.stdout)[-1]
    print(last_line, end="")
    process.wait()

    try:
        last_suggestion = int(last_line.split()[0])  # 提取建议的列号
        print(f"建议的列号: {last_suggestion}")
    except (ValueError, IndexError) as e:
        print(f"提取建议的列号失败: {e}")

def apply_move():
    global driver, last_suggestion
    if driver is not None:  # 确保浏览器已启动
        try:
            element_id = f"square_{last_suggestion}_1"
            element = driver.find_element(By.ID, element_id)
            
            # 使用 ActionChains 模拟鼠标点击
            actions = ActionChains(driver)
            actions.move_to_element(element).click().perform()
            
            print(f"已模拟点击元素: {element_id}")
            time.sleep(2)
            buttonupmost = driver.find_element(By.XPATH, "/html/body/div[3]/div[1]/div[1]")
            buttonupmost.click()
        except Exception as e:
            print(f"应用移动失败: {e}")
    else:
        print("浏览器未启动，请先打开浏览器。")

def search_text_in_page(driver, target_text):
    try:
        # 获取整个页面的文本
        page_text = driver.find_element("tag name", "body").text
        # 检查是否包含目标文本
        if target_text in page_text:
            print(f"找到了目标文本: {target_text}")
            return True
        else:
            print(f"未找到目标文本: {target_text}")
            return False
    except Exception as e:
        print(f"搜索页面文本时发生异常: {e}")
        return False


def cmd9():
    print("执行组合命令：更新游戏棋盘、调用外部程序、应用移动")
    update_gameboard()

    query_external_program()

    apply_move()

def cmd8():
    print("执行自动检测循环以自动玩游戏")
    global stop_flag
    stop_flag = False

    while not stop_flag:
        try:
            # 检测是否在游戏中
            ingame = False
            try:
                element = driver.find_element(By.ID, "pagemaintitletext")
                ingame = True
            except Exception:
                ingame = False

            if ingame:
                # 游戏中逻辑
                while ingame and not stop_flag:
                    try:
                        element = driver.find_element(By.ID, "pagemaintitletext")
                        if "游戏结束" in element.text:
                            ingame = False
                            playagainbutton = driver.find_element(By.ID, "createNew_btn")
                            playagainbutton.click()
                            time.sleep(3)
                            break
                        span = element.find_element(By.TAG_NAME, "span")
                        if span.text == "你":
                            print("检测到 '你'，执行 cmd9。")
                            cmd9()
                        elif "必须" in element.text:
                            time.sleep(1)
                    except Exception as e:
                        print(f"游戏中处理异常: {e}")
                        ingame = False
                        break
            else:
                # 游戏外逻辑
                try:
                    element = driver.find_element(By.ID, "pagemaintitletext")
                    print('找到了游戏标题')
                    if "游戏结束" in element.text:
                        playagainbutton = driver.find_element(By.ID, "createNew_btn")
                        playagainbutton.click()
                        print('点击了再来一次')
                        time.sleep(3)
                except Exception:
                    pass

                try:
                    startbtn = driver.find_element(By.XPATH, "/html/body/div[2]/div[5]/div/div[1]/div/div[3]/div/div/div/div[4]/div[2]/div/a")
                    startbtn.click()
                    print('点击了开始游戏（匹配）')

                    time.sleep(0.5)
                    count = 0
                    while search_text_in_page(driver=driver, target_text="正在搜寻玩家"):
                        if stop_flag:
                            return
                        time.sleep(1)
                        count = count + 1
                        print(f"等待匹配{count}秒")

                except Exception:
                    pass

                try:
                    WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.ID, "ags_start_game_accept"))
                    ).click()
                    print('点击了确认按钮')
                    WebDriverWait(driver, 18).until(
                        EC.presence_of_element_located((By.ID, "pagemaintitletext"))
                    )
                    print('在18秒内等待到了别人开始')
                except Exception:
                    print('等待确认按钮或者等待他人超时')
                    pass

        except Exception as e:
            print(f"cmd8 主循环异常，{e}")
            time.sleep(1)

def main():
    print("按键监听已启动：")
    print("1 - 打开浏览器并访问页面")
    print("2 - 登录操作")
    print("3 - 更新游戏棋盘")
    print("4 - 打印游戏棋盘")
    print("5 - 调用外部程序")
    print("7 - 应用移动")
    print("8 - 自动检测循环")
    print("9 - 执行组合命令")
    print("0 - 退出程序")

    while True:
        user_input = input("请输入指令 (1/2/3/4/5/7/8/9/0): ")
        if user_input == '1':
            open_browser()
        elif user_input == '2':
            continue
            login()
        elif user_input == '3':
            update_gameboard()
        elif user_input == '4':
            print_gameboard()
        elif user_input == '5':
            query_external_program()
        elif user_input == '7':
            apply_move()
        elif user_input == '8':
            cmd8()
        elif user_input == '9':
            cmd9()
        elif user_input == '0':
            print("退出程序。")
            close_browser()
            break
        else:
            print("无效指令，请重新输入。")

if __name__ == "__main__":
    main()