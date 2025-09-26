import argparse
import sys
import os

# 确保项目根目录在 Python 路径中
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import uvicorn
from core.database import init_db

def main():
    parser = argparse.ArgumentParser(description="AI 交易分析工具的管理脚本。")
    parser.add_argument('command', help='要运行的命令', choices=['init-db', 'run'])

    args = parser.parse_args()

    if args.command == 'init-db':
        print("正在初始化数据库...")
        try:
            init_db()
            print("数据库初始化成功。")
        except Exception as e:
            print(f"数据库初始化过程中发生错误: {e}")
            sys.exit(1)
    elif args.command == 'run':
        print("正在使用 uvicorn 启动 Web 服务器...")
        # 注意: 我们将应用字符串传递给 uvicorn.run()
        # --reload 标志由 uvicorn 的子进程管理处理
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    else:
        print(f"未知命令: {args.command}")
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()