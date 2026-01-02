# 统一题目自动选择系统

## 功能概述

`unified_auto_answer.py`是一个自动化答题系统，用于处理在线学习平台的答题页面。该系统支持单选题、多选题和判断题的自动识别和作答，并集成了DeepSeek AI接口进行智能答题。

## 核心功能

- **多题型支持**：自动识别和处理单选题、多选题和判断题
- **AI智能答题**：集成DeepSeek AI接口，自动获取题目答案
- **灵活的URL支持**：支持网络URL和本地HTML文件访问
- **安全验证机制**：包含URL验证、本地文件安全检查和权限验证
- **自动浏览器操作**：使用Selenium WebDriver自动控制浏览器
- **详细的日志记录**：记录系统执行过程和结果

## 核心算法说明

### 1. 题型识别算法

通过XPath定位不同题型区域：
- 单选题：默认题型，排除多选题和判断题区域后的题目
- 多选题：定位包含"多选题"文本的特征盒子下的题目
- 判断题：定位包含"判断题"文本的特征盒子下的题目

### 2. 题目和选项提取算法

从HTML元素中提取题目内容和选项：
- 题目内容：通过`div.qsctt`类定位
- 选项：通过`ul.xuan li`定位，支持多种选项格式（如"A. 选项内容"、"A、选项内容"等）

### 3. AI答题算法

1. 提取题目和选项
2. 组织提示词
3. 调用DeepSeek API获取答案
4. 解析AI返回结果

### 4. 自动答题算法

- 单选题：定位radio类型input元素，根据答案选择对应选项
- 多选题：定位checkbox类型input元素，选择所有符合条件的选项
- 判断题：定位包含"正确"和"错误"选项的radio元素，根据答案选择

## 配置参数

### 1. DeepSeek AI配置

```python
DEEPSEEK_CONFIG = {
    "api_key": "your_api_key",  # DeepSeek API密钥
    "api_url": "https://api.deepseek.com/v1/chat/completions",  # API地址
    "model": "deepseek-chat",  # 使用的AI模型
    "timeout": 30  # 请求超时时间
}
```

### 2. 浏览器配置

```python
BROWSER_CONFIG = {
    "use_existing_browser": True,  # 是否使用现有浏览器实例
    "debug_port": 9515,  # 调试端口
    "user_data_dir": r"C:\EdgeProfile",  # 浏览器配置文件目录
    "auto_start_browser": True  # 是否自动启动Edge浏览器
}
```

### 3. AI自动答题配置

```python
AI_AUTO_ANSWER_CONFIG = {
    "enabled": True,  # 是否启用AI自动答题
    "model": "deepseek-chat"  # 使用的AI模型
}
```

## 使用方法

### 1. 环境准备

- 安装Python 3.8+
- 安装依赖：
  ```bash
  pip install selenium requests
  ```
- 确保Edge浏览器已安装
- 下载对应版本的EdgeDriver，并添加到系统PATH

### 2. 配置API密钥

在代码中修改`DEEPSEEK_CONFIG["api_key"]`为你的DeepSeek API密钥。

### 3. 运行脚本

```bash
python unified_auto_answer.py
```

### 4. 输入URL

根据提示输入答题页面URL或本地HTML文件路径：
- 网络URL：如`https://ymun.ketangx.net/learn/NewExam?param=...`
- 本地文件：如`file:///C:/Users/questions.html`或`C:\Users\questions.html`

### 5. 登录处理

- 对于网络URL，系统会等待用户在浏览器中完成登录
- 对于本地文件，直接跳过登录验证

### 6. 自动答题

系统会自动识别题型并开始答题，答题过程会显示在控制台。

## 示例代码

### 基本使用

```bash
# 运行脚本
python unified_auto_answer.py

# 输入网络URL
请输入答题页面URL（例如：https://bilibili.com）或本地文件路径：(例如file:///C:/Users/questions.html)
https://ymun.ketangx.net/learn/NewExam?param=...

# 或输入本地文件路径
请输入答题页面URL（例如：https://bilibili.com）或本地文件路径：(例如file:///C:/Users/questions.html)
file:///C:/Users/Administrator/Downloads/questions.html
```

## 常见问题解答

### 1. URL验证失败

**问题**：输入的URL被提示格式无效

**解决方法**：
- 确保URL包含`learn/NewExam`路径
- 对于本地文件，确保路径格式正确
- 检查URL是否包含路径遍历字符（如`../`）

### 2. 浏览器启动失败

**问题**：无法启动或连接到Edge浏览器

**解决方法**：
- 确保Edge浏览器已安装
- 确保EdgeDriver与浏览器版本匹配
- 检查浏览器配置参数是否正确
- 尝试将`use_existing_browser`设置为`False`

### 3. AI答题失败

**问题**：AI无法获取答案或答案错误

**解决方法**：
- 检查DeepSeek API密钥是否有效
- 确保网络连接正常
- 检查题目提取是否正确

### 4. 题型识别错误

**问题**：题目被错误分类为其他题型

**解决方法**：
- 确保答题页面结构与预期一致
- 检查题型区域的XPath定位是否正确

## 维护注意事项

### 1. 代码结构

- 主函数`main()`包含系统的主要执行流程
- 各个题型处理函数负责特定题型的处理
- 配置参数集中在文件顶部，便于修改

### 2. 浏览器兼容性

- 系统使用Edge浏览器，确保与最新版本兼容
- 定期更新EdgeDriver以匹配浏览器版本

### 3. API依赖

- DeepSeek API可能会更新，需要关注API文档变化
- 建议使用环境变量存储API密钥，提高安全性

### 4. XPath维护

- 当答题页面结构变化时，需要更新相应的XPath表达式
- 重点关注题型识别和题目提取的XPath

### 5. 错误处理

- 系统包含详细的错误处理机制，但仍可能遇到未预见的错误
- 建议定期检查日志，了解系统运行情况

## 日志记录

系统使用Python logging模块记录日志，日志文件名为`deepseek_ai.log`，包含以下信息：
- API调用记录
- 题目和选项提取记录
- 答题结果记录
- 错误信息

## 许可证

本项目采用 **GPLv3开源协议**，严格遵守以下条款：

### 核心条款

1. **非商业用途**：**明确禁止**将本项目用于任何商业目的，包括但不限于：
   - 直接或间接获取经济利益
   - 用于商业产品或服务
   - 用于商业培训或教育
   - 用于商业研究或开发

2. **学习研究用途**：仅允许用于个人学习、学术研究和非盈利教育目的

3. **保留原作者信息**：二次开发、修改或分发时必须：
   - 保留所有原作者版权声明
   - 明确标明修改内容和修改者
   - 不得删除或修改原项目的许可证信息

4. **开源共享**：对本项目进行修改后，必须以相同协议开源发布，禁止闭源修改

5. **衍生作品**：基于本项目创建的衍生作品必须采用相同协议

6. **免责声明**：作者不对软件的使用后果承担任何责任，使用本软件即表示同意承担所有风险

### 附加限制声明

本项目基于GPLv3协议开源，同时额外增加以下限制：
1. 禁止将本项目的源代码、二进制文件，或其任何衍生作品（包括修改、改编、整合后的作品）用于任何商业用途，包括但不限于：
   - 以盈利为目的的售卖、分发；
   - 用于商业服务、产品开发、广告推广等商业活动；
   - 其他任何能直接或间接获得经济收益的使用场景。
2. 本附加声明是对GPLv3协议的补充，与GPLv3协议具有同等法律效力；若本声明与GPLv3协议存在冲突，以本附加声明为准。

### 适用范围

本许可证适用于项目的所有代码、文档和相关资源。

### 违规处理

违反本许可证条款的行为将受到法律追究，作者保留追究法律责任的权利。

### 许可证兼容性

本协议与以下开源协议不兼容：
- MIT License
- Apache License 2.0
- BSD License
- GPL v2/v3（由于商业用途限制）

### 联系信息

如需商业授权或其他特殊用途，请联系项目作者。

## 联系方式

如有问题或建议，欢迎提交Issue或Pull Request。