#!/usr/bin/env python3
import os
import platform
import subprocess
import sys
import shutil

def build():
    print("开始构建 运维辅助工具 GUI...")

    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('main.build'):
        shutil.rmtree('main.build')
    if os.path.exists('main.dist'):
        shutil.rmtree('main.dist')

    system = platform.system().lower()
    arch = platform.machine().lower()
    
    if arch in ['x86_64', 'amd64']:
        arch_name = 'x64'
    elif arch in ['arm64', 'aarch64']:
        arch_name = 'arm64'
    else:
        arch_name = arch

    if system == 'windows':
        output_name = f'niuma-windows-{arch_name}.exe'
    elif system == 'linux':
        output_name = f'niuma-linux-{arch_name}'
    elif system == 'darwin':
        output_name = f'niuma-macos-{arch_name}'
    else:
        output_name = f'niuma-{system}-{arch_name}'

    cmd = [
        sys.executable, '-m', 'nuitka',
        '--standalone',
        '--onefile',
        '--enable-plugin=pyqt6',
        '--follow-imports',
        '--nofollow-import-to=tkinter,matplotlib,numpy,pandas,scipy',
        '--output-dir=dist',
        f'--output-filename={output_name}',
        '--assume-yes-for-downloads',
        'main.py'
    ]

    if system == 'windows':
        cmd.insert(4, '--windows-disable-console')
    else:
        cmd.insert(4, '--disable-console')
        cmd.append('--lto=yes')

    print(f"执行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print(f"构建成功！可执行文件: dist/{output_name}")
    else:
        print("构建失败")
        sys.exit(1)

if __name__ == '__main__':
    build()
