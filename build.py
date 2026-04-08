#!/usr/bin/env python3
import os
import subprocess
import sys

def build():
    print("开始构建 Niuma GUI...")

    # 清理旧的构建文件
    if os.path.exists('build'):
        subprocess.run(['rm', '-rf', 'build'])
    if os.path.exists('dist'):
        subprocess.run(['rm', '-rf', 'dist'])

    # 运行 PyInstaller
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        'pyinstaller.spec'
    ]

    print(f"执行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("构建成功！可执行文件在 dist/ 目录下")
    else:
        print("构建失败")
        sys.exit(1)

if __name__ == '__main__':
    build()
