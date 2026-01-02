@echo off
REM 切换到当前脚本所在目录
cd /d "%~dp0"

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo Python 未安装或未添加到系统环境变量
    echo 请先安装 Python 并添加到 PATH
    pause
    exit /b 1
)

REM 运行 Python 脚本
echo 正在运行 unified_auto_answer.py ...
python unified_auto_answer.py

REM 如果脚本运行完毕，暂停查看结果
if errorlevel 0 (
    echo 脚本执行完成
) else (
    echo 脚本执行出错，错误代码: %errorlevel%
)
pause