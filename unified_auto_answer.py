from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, ElementNotInteractableException,
    StaleElementReferenceException
)
import time
import traceback
import requests
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deepseek_ai.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DeepSeekAI')

# DeepSeek AI 配置
DEEPSEEK_CONFIG = {
    "api_key": "your_api_key",  # 请替换为您的DeepSeek API密钥
    "api_url": "https://api.deepseek.com/v1/chat/completions",
    "model": "deepseek-chat",
    "timeout": 30
}

# 配置参数
URL = None

# 初始化系统配置

def init_config():
    """初始化系统配置，包括URL的手动输入和验证"""
    global URL
    
    print("=" * 50)
    print("统一题目自动选择系统 - 配置初始化")
    print("=" * 50)
    
    while True:
        try:
            # 提示用户输入URL
            user_input = input("请输入答题页面URL（例如：https://bilibili.com）或本地文件路径：(例如file:///C:/Users/questions.html)\n")
            
            # 移除输入前后的空格
            user_input = user_input.strip()
            
            # 验证URL是否为空
            if not user_input:
                print("❌ URL不能为空，请重新输入！\n")
                continue
            
            # 验证URL格式是否有效
            is_web_url = False
            is_local_file = False
            
            if user_input.startswith("http://") or user_input.startswith("https://"):
                is_web_url = True
            elif user_input.startswith("file://"):
                is_local_file = True
            elif user_input.startswith("C:") or user_input.startswith("D:") or user_input.startswith("E:"):
                # 本地绝对路径
                is_local_file = True
                # 转换为file://协议格式
                user_input = f"file:///{user_input.replace('\\', '/')}"
            
            if not (is_web_url or is_local_file):
                print("❌ URL格式无效，请确保URL以http://、https://、file://开头，或为本地绝对路径！\n")
                continue
            
            # 安全检查：防止路径遍历攻击
            if is_local_file:
                # 检查是否包含路径遍历字符
                if "../" in user_input or "..\\" in user_input:
                    print("❌ 检测到潜在的路径遍历攻击，禁止访问！\n")
                    continue
                
                # 检查文件是否存在
                try:
                    import os
                    # 从file://URL中提取本地文件路径
                    if user_input.startswith("file://"):
                        local_path = user_input[8:].replace('/', '\\')
                        # 处理Windows路径，移除多余的反斜杠
                        if local_path.startswith("\\"):
                            local_path = local_path[1:]
                    else:
                        local_path = user_input
                    
                    if not os.path.exists(local_path):
                        print(f"❌ 本地文件不存在：{local_path}\n")
                        continue
                    
                    if not os.path.isfile(local_path):
                        print(f"❌ 路径不是文件：{local_path}\n")
                        continue
                    
                    # 验证文件权限
                    if not os.access(local_path, os.R_OK):
                        print(f"❌ 无法访问文件：{local_path}，权限不足！\n")
                        continue
                    
                    print(f"✅ 本地文件验证成功：{local_path}")
                except Exception as e:
                    print(f"❌ 本地文件验证失败：{e}\n")
                    continue
            
            # 对于网络URL，验证必要参数
            if is_web_url:
                # 放宽验证条件：只检查是否包含learn/NewExam路径
                if "learn/NewExam" not in user_input:
                    print("❌ 请输入有效的答题页面URL，确保包含learn/NewExam路径！\n")
                    continue
            
            # 验证通过，设置URL
            URL = user_input
            print(f"✅ URL设置成功：{URL}")
            print("=" * 50)
            break
            
        except KeyboardInterrupt:
            print("\n\n❌ 用户取消输入，程序退出！")
            exit(1)
        except Exception as e:
            print(f"\n❌ 输入过程中发生错误：{e}，请重新输入！\n")
            continue

# AI自动答题配置
AI_AUTO_ANSWER_CONFIG = {
    "enabled": True,  # 是否启用AI自动答题
    "model": "deepseek-chat"  # 使用的AI模型
}

# 浏览器运行模式配置
BROWSER_CONFIG = {
    "use_existing_browser": True,  # 是否使用现有浏览器实例（True：使用现有实例，False：启动新实例）
    "debug_port": 9515,  # 调试端口（仅use_existing_browser=True时有效）
    "user_data_dir": r"C:\EdgeProfile",  # 浏览器配置文件目录
    "auto_start_browser": True  # 是否自动启动Edge浏览器（仅use_existing_browser=True时有效）
}

# 单选题答案（从auto_answer.py导入）
SINGLE_CHOICE_ANSWERS = {}

# 多选题标准答案
MULTIPLE_CHOICE_ANSWERS = {}

# 判断题标准答案
TRUE_FALSE_ANSWERS = {}

# 系统状态常量
class SystemStatus:
    NOT_STARTED = "not_started"
    SINGLE_CHOICE_PROCESSING = "single_choice_processing"
    SINGLE_CHOICE_COMPLETED = "single_choice_completed"
    MULTIPLE_CHOICE_PROCESSING = "multiple_choice_processing"
    MULTIPLE_CHOICE_COMPLETED = "multiple_choice_completed"
    TRUE_FALSE_PROCESSING = "true_false_processing"
    TRUE_FALSE_COMPLETED = "true_false_completed"
    ALL_COMPLETED = "all_completed"
    ERROR = "error"

# 错误类型常量
class ErrorType:
    DATA_STRUCTURE_ERROR = "data_structure_error"
    ANSWER_FORMAT_ERROR = "answer_format_error"
    PROCESSING_INTERRUPTED = "processing_interrupted"
    ELEMENT_NOT_FOUND = "element_not_found"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"
    API_REQUEST_FAILED = "api_request_failed"
    API_RESPONSE_ERROR = "api_response_error"
    API_PARSE_ERROR = "api_parse_error"

# 调用DeepSeek AI接口
def call_deepseek_api(prompt):
    """调用DeepSeek AI接口获取答案
    
    Args:
        prompt (str): 组织好的提示词
        
    Returns:
        str: 推荐的答案选项，如"A"、"B C"等
        None: 如果调用失败
    """
    try:
        logger.info(f"调用DeepSeek API，提示词长度: {len(prompt)}")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_CONFIG['api_key']}"
        }
        
        payload = {
            "model": DEEPSEEK_CONFIG["model"],
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位专业的答题助手，请根据提供的题目和选项，选择正确的答案。只需要返回答案选项，如'A'、'B C'、'正确'等，不需要任何解释。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 100
        }
        
        # 发送API请求
        response = requests.post(
            DEEPSEEK_CONFIG["api_url"],
            headers=headers,
            json=payload,
            timeout=DEEPSEEK_CONFIG["timeout"]
        )
        
        # 检查响应状态码
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        logger.info(f"DeepSeek API响应成功，结果: {result}")
        
        # 提取答案
        answer = result["choices"][0]["message"]["content"].strip()
        logger.info(f"提取到答案: {answer}")
        
        return answer
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API请求失败: {e}")
        return None
    except KeyError as e:
        logger.error(f"API响应解析失败，缺少字段: {e}")
        return None
    except Exception as e:
        logger.error(f"API调用过程中发生未知错误: {e}")
        traceback.print_exc()
        return None

# 从题目元素中提取题目和选项
def extract_question_and_options(question_element):
    """从题目元素中提取题目和选项
    
    Args:
        question_element: 题目元素对象
        
    Returns:
        dict: 包含题目和选项的字典
    """
    try:
        # 提取题目内容
        question_xpath = ".//div[@class='qsctt']"
        question_content = question_element.find_element(By.XPATH, question_xpath).text.strip()
        logger.info(f"提取到题目: {question_content}")
        
        # 提取选项
        options_xpath = ".//ul[@class='xuan']/li"
        option_elements = question_element.find_elements(By.XPATH, options_xpath)
        
        options = []
        for option_element in option_elements:
            option_text = option_element.text.strip()
            # 处理多种选项格式，如"A. 选项内容"、"A . 选项内容"、"A、选项内容"等
            logger.info(f"原始选项文本: {option_text}")
            
            # 提取选项字母和内容
            option_letter = None
            option_content = None
            
            # 尝试多种分隔符
            for separator in ['. ', '.', '、', ' ']:
                if separator in option_text:
                    parts = option_text.split(separator, 1)
                    if len(parts) == 2:
                        option_letter = parts[0].strip()
                        option_content = parts[1].strip()
                        break
            
            # 处理没有明确分隔符的情况，如"A选项内容"
            if not option_letter and len(option_text) > 1:
                # 假设第一个字符是选项字母
                option_letter = option_text[0].strip()
                option_content = option_text[1:].strip()
            
            if option_letter and option_content:
                options.append((option_letter, option_content))
                logger.info(f"提取到选项: {option_letter}. {option_content}")
            else:
                # 处理特殊格式
                logger.warning(f"选项格式异常: {option_text}")
        
        logger.info(f"最终提取到选项: {options}")
        
        return {
            "question": question_content,
            "options": options
        }
        
    except Exception as e:
        logger.error(f"提取题目和选项失败: {e}")
        traceback.print_exc()
        return None

# 组织提示词
def organize_prompt(question, options):
    """将题目和选项组织成提示词
    
    Args:
        question (str): 题目内容
        options (list): 选项列表，每个元素为(选项字母, 选项内容)
        
    Returns:
        str: 组织好的提示词
    """
    try:
        prompt = f"题目: {question}\n选项:\n"
        
        for option_letter, option_content in options:
            prompt += f"{option_letter}. {option_content}\n"
        
        prompt += "请选择正确答案，只需要返回答案选项，如'A'、'B C'、'正确'等，不需要任何解释。"
        
        logger.info(f"组织好的提示词: {prompt}")
        return prompt
        
    except Exception as e:
        logger.error(f"组织提示词失败: {e}")
        return None

# 自动获取题目答案
def auto_get_answer(question_element):
    """自动获取题目答案
    
    Args:
        question_element: 题目元素对象
        
    Returns:
        str: 推荐的答案选项
        None: 如果获取失败
    """
    try:
        # 1. 提取题目和选项
        extracted = extract_question_and_options(question_element)
        if not extracted:
            return None
        
        # 2. 组织提示词
        prompt = organize_prompt(extracted["question"], extracted["options"])
        if not prompt:
            return None
        
        # 3. 调用DeepSeek API
        answer = call_deepseek_api(prompt)
        
        return answer
        
    except Exception as e:
        logger.error(f"自动获取答案失败: {e}")
        traceback.print_exc()
        return None

# 初始化WebDriver
def init_driver():
    """初始化Microsoft Edge WebDriver"""
    try:
        # 如果需要使用现有浏览器实例
        if BROWSER_CONFIG["use_existing_browser"]:
            # 检查是否需要自动启动浏览器
            if BROWSER_CONFIG["auto_start_browser"]:
                print("正在以调试模式启动Edge浏览器...")
                # 启动Edge浏览器（调试模式）
                import subprocess
                subprocess.Popen([
                    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                    f"--remote-debugging-port={BROWSER_CONFIG['debug_port']}",
                    f"--user-data-dir={BROWSER_CONFIG['user_data_dir']}"
                ])
                print(f"✓ Edge浏览器已启动，调试端口：{BROWSER_CONFIG['debug_port']}")
                time.sleep(3)  # 等待浏览器启动完成
            
            # 创建Edge选项，配置连接到现有浏览器实例
            edge_options = Options()
            edge_options.add_argument(f"--remote-debugging-port={BROWSER_CONFIG['debug_port']}")
            edge_options.add_argument(f"--user-data-dir={BROWSER_CONFIG['user_data_dir']}")
            edge_options.add_argument("--start-maximized")
            edge_options.add_argument("--disable-extensions")
            edge_options.add_argument("--disable-gpu")
            edge_options.add_argument("--no-sandbox")
            
            # 配置连接到现有浏览器实例
            edge_options.add_experimental_option(
                "debuggerAddress", 
                f"127.0.0.1:{BROWSER_CONFIG['debug_port']}"
            )
            
            # 初始化Edge WebDriver，连接到现有实例
            driver = webdriver.Edge(
                options=edge_options,
                service=EdgeService()
            )
            
            print(f"✓ 成功连接到现有Edge浏览器实例（端口：{BROWSER_CONFIG['debug_port']}")
            return driver
        else:
            # 启动新的浏览器实例
            edge_options = Options()
            edge_options.add_argument("--start-maximized")
            edge_options.add_argument("--disable-extensions")
            edge_options.add_argument("--disable-gpu")
            edge_options.add_argument("--no-sandbox")
            edge_options.add_argument("--ignore-certificate-errors")
            edge_options.add_argument("--allow-insecure-localhost")
            
            # 初始化Edge WebDriver
            driver = webdriver.Edge(
                options=edge_options,
                service=EdgeService()
            )
            
            print("✓ 成功启动新的Edge浏览器实例")
            return driver
    except Exception as e:
        print(f"✗ 初始化Edge浏览器失败：{e}")
        print("错误详情：")
        traceback.print_exc()
        print("\n请检查：")
        if BROWSER_CONFIG["use_existing_browser"]:
            print(f"1. 是否已以调试模式启动Edge浏览器（端口：{BROWSER_CONFIG['debug_port']}")
            print(f"2. 命令：msedge.exe --remote-debugging-port={BROWSER_CONFIG['debug_port']} --user-data-dir={BROWSER_CONFIG['user_data_dir']}")
            print("3. 浏览器是否已正常运行")
        else:
            print("1. EdgeDriver是否与Edge浏览器版本匹配")
            print("2. EdgeDriver是否已添加到系统环境变量PATH中")
            print("3. 是否有足够的权限运行浏览器")
        raise

# 检测登录弹窗
def handle_login_popup(driver):
    """处理可能出现的登录弹窗"""
    try:
        # 等待可能出现的登录弹窗
        alert = WebDriverWait(driver, 5).until(EC.alert_is_present())
        alert_text = alert.text
        print(f"\n检测到登录弹窗：{alert_text}")
        alert.accept()  # 关闭弹窗
        print("已关闭登录弹窗")
        return True
    except TimeoutException:
        print("未检测到登录弹窗")
        return False

# 手动登录等待
def wait_for_manual_login(driver):
    """等待用户手动完成登录"""
    print("\n" + "=" * 50)
    print("手动登录模式")
    print("=" * 50)
    input("请在浏览器中完成登录，登录成功后按回车键继续...")
    
    # 验证登录是否成功
    print("\n正在验证登录状态...")
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class='test_paper']"))
        )
        print("✓ 登录成功")
        return True
    except TimeoutException:
        print("✗ 登录验证失败，未找到答题页面特征元素")
        input("按回车键退出...")
        return False

# 处理单选题（从auto_answer.py提取的核心逻辑）
def process_single_choice(driver):
    """处理单选题"""
    print("\n" + "=" * 50)
    print("开始处理单选题")
    print("=" * 50)
    
    results = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'failed_details': []
    }
    
    try:
        # 定位所有单选题容器
        # 获取所有test_paper元素
        all_question_containers = driver.find_elements(By.XPATH, "//div[@class='test_paper']")
        
        # 检测多选题和判断题区域，以区分不同题型
        multiple_choice_containers = []
        true_false_containers = []
        single_choice_containers = []
        
        # 检测多选题区域
        multiple_choice_xpath = "//div[@class='uniterming border-all' and contains(text(), '多选题')]"
        try:
            multiple_choice_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, multiple_choice_xpath))
            )
            # 获取多选题区域的父容器
            multiple_choice_parent = multiple_choice_element.find_element(By.XPATH, "..")
            # 获取多选题区域内的题目容器
            multiple_choice_containers = multiple_choice_parent.find_elements(By.XPATH, ".//div[@class='test_paper']")
            print(f"  检测到多选题区域，包含 {len(multiple_choice_containers)} 道题")
        except Exception:
            print("  未检测到多选题区域")
        
        # 检测判断题区域
        true_false_xpath = "//div[@class='uniterming border-all' and contains(text(), '判断题')]"
        try:
            true_false_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, true_false_xpath))
            )
            # 获取判断题区域的父容器
            true_false_parent = true_false_element.find_element(By.XPATH, "..")
            # 获取判断题区域内的题目容器
            true_false_containers = true_false_parent.find_elements(By.XPATH, ".//div[@class='test_paper']")
            print(f"  检测到判断题区域，包含 {len(true_false_containers)} 道题")
        except Exception:
            print("  未检测到判断题区域")
        
        # 区分单选题、多选题和判断题容器
        for container in all_question_containers:
            if container not in multiple_choice_containers and container not in true_false_containers:
                single_choice_containers.append(container)
        
        results['total'] = len(single_choice_containers)
        print(f"共检测到 {results['total']} 道单选题")
        
        # 遍历所有单选题并答题
        for idx, target_question in enumerate(single_choice_containers):
            question_num = idx + 1
            try:
                print(f"\n正在处理单选题第 {question_num} 题")
                
                # 将页面滚动到当前题目位置
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", target_question)
                time.sleep(0.5)
                
                answer = None
                
                # 如果启用AI自动答题
                if AI_AUTO_ANSWER_CONFIG["enabled"]:
                    print("  使用AI自动获取答案...")
                    # 自动获取答案
                    ai_answer = auto_get_answer(target_question)
                    if ai_answer:
                        print(f"  AI推荐答案：{ai_answer}")
                        answer = ai_answer
                    else:
                        print(f"  ✗ AI获取答案失败，跳过此题")
                        results['failed'] += 1
                        results['failed_details'].append(f"题目 {question_num} (AI获取答案失败)")
                        continue
                else:
                    # 使用预设答案
                    if question_num in SINGLE_CHOICE_ANSWERS:
                        answer = SINGLE_CHOICE_ANSWERS[question_num]
                        print(f"  预设答案：{answer}")
                    else:
                        print(f"  ✗ 未找到题目 {question_num} 的预设答案")
                        results['failed'] += 1
                        results['failed_details'].append(f"题目 {question_num} (无预设答案)")
                        continue
                
                # 定位并点击选项
                # 定位题目元素中的radio input
                radio_xpath = f".//input[@type='radio' and @value='{answer}']"
                radio_element = WebDriverWait(target_question, 5).until(
                    EC.element_to_be_clickable((By.XPATH, radio_xpath))
                )
                
                if not radio_element.is_selected():
                    radio_element.click()
                    results['success'] += 1
                    print(f"✓ 题目 {question_num} 成功选择答案：{answer}")
                else:
                    results['success'] += 1
                    print(f"✓ 题目 {question_num} 答案 {answer} 已被选中")
                    
                time.sleep(0.3)  # 等待选择完成
                
            except Exception as e:
                results['failed'] += 1
                results['failed_details'].append(f"题目 {question_num}")
                print(f"✗ 处理题目 {question_num} 失败：{e}")
                traceback.print_exc()
                continue
        
        # 输出单选题处理结果
        print("\n" + "=" * 50)
        print("=== 单选题处理结果 ===")
        print(f"总题目数：{results['total']}")
        print(f"成功答题：{results['success']}")
        print(f"失败答题：{results['failed']}")
        
        # 计算成功率，避免除以零
        if results['total'] > 0:
            success_rate = (results['success'] / results['total']) * 100
            print(f"成功率：{success_rate:.1f}%")
        else:
            print("成功率：0.0% (没有可处理的单选题)")
        
        if results['failed_details']:
            print("\n失败详情：")
            for detail in results['failed_details']:
                print(f"  - {detail}")
        
        return True  # 即使没有单选题，也返回True，让程序继续执行后续题型处理
        
    except Exception as e:
        print(f"\n✗ 处理单选题过程中发生严重错误：{e}")
        print("错误详情：")
        traceback.print_exc()
        return True  # 即使发生错误，也返回True，让程序继续执行后续题型处理

# 检测题型区域
def detect_question_types(driver):
    """检测多选题和判断题题型区域"""
    print("\n" + "=" * 50)
    print("开始检测题型区域")
    print("=" * 50)
    
    question_types = {
        "multiple_choice": None,
        "true_false": None
    }
    
    try:
        # 检测多选题区域
        multiple_choice_xpath = "//div[@class='uniterming border-all' and contains(text(), '多选题')]"
        try:
            multiple_choice_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, multiple_choice_xpath))
            )
            multiple_choice_parent = multiple_choice_element.find_element(By.XPATH, "..")
            question_types["multiple_choice"] = multiple_choice_parent
            print(f"✓ 成功检测到多选题题型区域")
            print(f"  多选题区域容器：{multiple_choice_parent.get_attribute('id')}")
        except Exception as e:
            print(f"✗ 检测多选题题型区域失败：{e}")
        
        # 检测判断题区域
        true_false_xpath = "//div[@class='uniterming border-all' and contains(text(), '判断题')]"
        try:
            true_false_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, true_false_xpath))
            )
            true_false_parent = true_false_element.find_element(By.XPATH, "..")
            question_types["true_false"] = true_false_parent
            print(f"✓ 成功检测到判断题题型区域")
            print(f"  判断题区域容器：{true_false_parent.get_attribute('id')}")
        except Exception as e:
            print(f"✗ 检测判断题题型区域失败：{e}")
        
        return question_types
        
    except Exception as e:
        print(f"✗ 检测题型区域过程中发生严重错误：{e}")
        print("错误详情：")
        traceback.print_exc()
        return question_types

# 处理多选题（从auto_answer_specific.py提取的核心逻辑）
def process_multiple_choice(driver, question_area):
    """处理多选题"""
    print("\n" + "=" * 50)
    print("开始处理多选题")
    print("=" * 50)
    
    results = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'failed_details': []
    }
    
    try:
        # 获取所有多选题容器
        question_containers = question_area.find_elements(By.XPATH, ".//div[@class='test_paper']")
        results['total'] = len(question_containers)
        print(f"共检测到 {results['total']} 道多选题")
        
        # 遍历所有多选题并答题
        for idx, target_question in enumerate(question_containers):
            question_num = idx + 1
            try:
                print(f"\n正在处理多选题第 {question_num} 题")
                
                # 将页面滚动到当前题目位置
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", target_question)
                time.sleep(0.5)
                
                options_to_select = []
                
                # 如果启用AI自动答题
                if AI_AUTO_ANSWER_CONFIG["enabled"]:
                    print("  使用AI自动获取答案...")
                    # 自动获取答案
                    answer = auto_get_answer(target_question)
                    if answer:
                        # 解析答案，如"A B C" -> ["A", "B", "C"]
                        options_to_select = [opt.strip() for opt in answer.split() if opt.strip()]
                        print(f"  AI推荐答案：{options_to_select}")
                    else:
                        print(f"  ✗ AI获取答案失败，跳过此题")
                        results['failed'] += 1
                        results['failed_details'].append(f"题目 {question_num} (AI获取答案失败)")
                        continue
                else:
                    # 使用预设答案
                    if question_num in MULTIPLE_CHOICE_ANSWERS:
                        options_to_select = MULTIPLE_CHOICE_ANSWERS[question_num]
                        print(f"  预设答案：{options_to_select}")
                    else:
                        print(f"  ✗ 未找到题目 {question_num} 的预设答案")
                        results['failed'] += 1
                        results['failed_details'].append(f"题目 {question_num} (无预设答案)")
                        continue
                
                # 定位并选择所有指定选项
                selected_count = 0
                for option in options_to_select:
                    try:
                        option_xpath = f".//input[@type='checkbox' and @value='{option}']"
                        checkbox_element = WebDriverWait(target_question, 5).until(
                            EC.element_to_be_clickable((By.XPATH, option_xpath))
                        )
                        
                        if not checkbox_element.is_selected():
                            checkbox_element.click()
                            selected_count += 1
                            print(f"  ✓ 已选择选项 {option}")
                        else:
                            print(f"  ⚠ 选项 {option} 已被选中")
                            selected_count += 1
                            
                    except Exception as e:
                        print(f"  ✗ 选择选项 {option} 失败：{e}")
                        continue
                
                # 验证选择结果
                if selected_count == len(options_to_select):
                    results['success'] += 1
                    print(f"✓ 多选题第 {question_num} 题作答成功")
                else:
                    results['failed'] += 1
                    results['failed_details'].append(f"题目 {question_num}")
                    print(f"✗ 多选题第 {question_num} 题作答失败，仅成功选择 {selected_count}/{len(options_to_select)} 个选项")
                    
            except Exception as e:
                results['failed'] += 1
                results['failed_details'].append(f"题目 {question_num}")
                print(f"✗ 处理多选题第 {question_num} 题失败：{e}")
                traceback.print_exc()
                continue
        
        # 输出多选题处理结果
        print("\n" + "=" * 50)
        print("=== 多选题处理结果 ===")
        print(f"总题目数：{results['total']}")
        print(f"成功答题：{results['success']}")
        print(f"失败答题：{results['failed']}")
        print(f"成功率：{results['success']/results['total']*100:.1f}%")
        
        if results['failed_details']:
            print("\n失败详情：")
            for detail in results['failed_details']:
                print(f"  - {detail}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 处理多选题过程中发生严重错误：{e}")
        print("错误详情：")
        traceback.print_exc()
        return False

# 处理判断题（从auto_answer_specific.py提取的核心逻辑）
def process_true_false(driver, question_area):
    """处理判断题"""
    print("\n" + "=" * 50)
    print("开始处理判断题")
    print("=" * 50)
    
    results = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'failed_details': []
    }
    
    try:
        # 获取所有判断题容器
        question_containers = question_area.find_elements(By.XPATH, ".//div[@class='test_paper']")
        results['total'] = len(question_containers)
        print(f"共检测到 {results['total']} 道判断题")
        
        # 遍历所有判断题并答题
        for idx, target_question in enumerate(question_containers):
            question_num = idx + 1
            try:
                print(f"\n正在处理判断题第 {question_num} 题")
                
                # 将页面滚动到当前题目位置
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", target_question)
                time.sleep(0.5)
                
                option = None
                
                # 如果启用AI自动答题
                if AI_AUTO_ANSWER_CONFIG["enabled"]:
                    print("  使用AI自动获取答案...")
                    # 自动获取答案
                    answer = auto_get_answer(target_question)
                    if answer:
                        print(f"  AI推荐答案：{answer}")
                        option = answer
                    else:
                        print(f"  ✗ AI获取答案失败，跳过此题")
                        results['failed'] += 1
                        results['failed_details'].append(f"题目 {question_num} (AI获取答案失败)")
                        continue
                else:
                    # 使用预设答案
                    if question_num in TRUE_FALSE_ANSWERS:
                        option = TRUE_FALSE_ANSWERS[question_num]
                        print(f"  预设答案：{option}")
                    else:
                        print(f"  ✗ 未找到题目 {question_num} 的预设答案")
                        results['failed'] += 1
                        results['failed_details'].append(f"题目 {question_num} (无预设答案)")
                        continue
                
                # 定位并选择选项
                option_found = False
                
                # 1. 尝试直接定位包含"正确"或"错误"文本的label元素（推荐方法）
                try:
                    # 根据答案选择对应的label
                    if option == "正确" or option == "A":
                        option_text = "正确"
                    else:
                        option_text = "错误"
                    
                    # 使用新的XPath来定位判断题选项
                    label_xpath = f".//label[@class='radi' and contains(., '{option_text}')]"
                    label_element = WebDriverWait(target_question, 5).until(
                        EC.element_to_be_clickable((By.XPATH, label_xpath))
                    )
                    
                    # 点击label元素来选择选项
                    label_element.click()
                    print(f"  ✓ 已选择选项：{option_text} (通过label定位)")
                    option_found = True
                except Exception as e:
                    print(f"  尝试通过label定位失败：{e}")
                
                # 2. 如果第一种方法失败，尝试定位radio input元素
                if not option_found:
                    try:
                        if option == "正确" or option == "A":
                            # 查找包含"正确"文本的选项
                            radio_xpath = ".//label[@class='radi' and contains(., '正确')]//input[@type='radio']"
                        else:
                            # 查找包含"错误"文本的选项
                            radio_xpath = ".//label[@class='radi' and contains(., '错误')]//input[@type='radio']"
                        
                        radio_element = WebDriverWait(target_question, 5).until(
                            EC.element_to_be_clickable((By.XPATH, radio_xpath))
                        )
                        
                        radio_element.click()
                        print(f"  ✓ 已选择选项：{option} (通过radio input定位)")
                        option_found = True
                    except Exception as e:
                        print(f"  尝试通过radio input定位失败：{e}")
                
                # 3. 如果前两种方法都失败，尝试更通用的定位方式
                if not option_found:
                    try:
                        # 查找所有radio类型的input元素
                        radio_elements = target_question.find_elements(By.XPATH, ".//input[@type='radio']")
                        if len(radio_elements) >= 2:
                            # 假设第一个是"正确"，第二个是"错误"
                            if option == "正确" or option == "A":
                                radio_element = radio_elements[0]
                                option_text = "正确"
                            else:
                                radio_element = radio_elements[1]
                                option_text = "错误"
                            
                            radio_element.click()
                            print(f"  ✓ 已选择选项：{option_text} (通过索引定位)")
                            option_found = True
                    except Exception as e:
                        print(f"  尝试通过索引定位失败：{e}")
                
                if option_found:
                    results['success'] += 1
                    print(f"✓ 判断题第 {question_num} 题作答成功")
                else:
                    results['failed'] += 1
                    results['failed_details'].append(f"题目 {question_num}")
                    print(f"✗ 判断题第 {question_num} 题作答失败")
                    
            except Exception as e:
                results['failed'] += 1
                results['failed_details'].append(f"题目 {question_num}")
                print(f"✗ 处理判断题第 {question_num} 题失败：{e}")
                traceback.print_exc()
                continue
        
        # 输出判断题处理结果
        print("\n" + "=" * 50)
        print("=== 判断题处理结果 ===")
        print(f"总题目数：{results['total']}")
        print(f"成功答题：{results['success']}")
        print(f"失败答题：{results['failed']}")
        print(f"成功率：{results['success']/results['total']*100:.1f}%")
        
        if results['failed_details']:
            print("\n失败详情：")
            for detail in results['failed_details']:
                print(f"  - {detail}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 处理判断题过程中发生严重错误：{e}")
        print("错误详情：")
        traceback.print_exc()
        return False

# 主函数
def main():
    """统一的题目自动选择系统主函数"""
    driver = None
    system_status = SystemStatus.NOT_STARTED
    
    try:
        # 初始化系统配置
        init_config()
        
        # 初始化系统
        print("=== 统一题目自动选择系统 ===")
        print(f"执行时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"目标URL：{URL}")
        
        # 初始化浏览器
        driver = init_driver()
        system_status = SystemStatus.SINGLE_CHOICE_PROCESSING
        
        # 打开目标网页
        print(f"\n正在打开网页：{URL}")
        driver.get(URL)
        
        # 处理登录弹窗
        handle_login_popup(driver)
        
        # 等待手动登录
        if not wait_for_manual_login(driver):
            return
        
        # 处理单选题
        if process_single_choice(driver):
            system_status = SystemStatus.SINGLE_CHOICE_COMPLETED
        else:
            system_status = SystemStatus.SINGLE_CHOICE_COMPLETED
            print("\n✗ 单选题处理失败，但继续执行后续题型处理")
        
        # 检测多选题和判断题题型区域
        question_types = detect_question_types(driver)
        
        # 处理多选题
        if question_types["multiple_choice"]:
            system_status = SystemStatus.MULTIPLE_CHOICE_PROCESSING
            if not process_multiple_choice(driver, question_types["multiple_choice"]):
                system_status = SystemStatus.ERROR
                print("\n✗ 多选题处理失败")
            else:
                system_status = SystemStatus.MULTIPLE_CHOICE_COMPLETED
        else:
            print("\n未检测到多选题题型区域，跳过多选题处理")
            system_status = SystemStatus.MULTIPLE_CHOICE_COMPLETED
        
        # 处理判断题
        if question_types["true_false"]:
            system_status = SystemStatus.TRUE_FALSE_PROCESSING
            if not process_true_false(driver, question_types["true_false"]):
                system_status = SystemStatus.ERROR
                print("\n✗ 判断题处理失败")
            else:
                system_status = SystemStatus.TRUE_FALSE_COMPLETED
        else:
            print("\n未检测到判断题题型区域，跳过判断题处理")
            system_status = SystemStatus.TRUE_FALSE_COMPLETED
        
        # 所有题目处理完成
        system_status = SystemStatus.ALL_COMPLETED
        print("\n" + "=" * 50)
        print("=== 所有题目处理完成 ===")
        print("=" * 50)
        print("✓ 系统执行成功")
        print(f"系统状态：{system_status}")
        
        # 等待用户查看结果
        input("\n按回车键关闭浏览器...")
        
    except Exception as e:
        system_status = SystemStatus.ERROR
        print(f"\n✗ 系统执行过程中发生严重错误：{e}")
        print("错误详情：")
        traceback.print_exc()
        input("\n按回车键关闭浏览器...")
    finally:
        # 关闭浏览器
        if driver and not BROWSER_CONFIG["use_existing_browser"]:
            print("\n正在关闭浏览器...")
            driver.quit()
            print("✓ 浏览器已关闭")
        elif BROWSER_CONFIG["use_existing_browser"]:
            print("\n使用现有浏览器实例，不会自动关闭浏览器")
        
        print(f"\n=== 系统执行完毕，最终状态：{system_status} ===")

# 执行主函数
if __name__ == "__main__":
    main()
