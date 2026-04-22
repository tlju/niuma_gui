#!/usr/bin/env python3
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile

def build():
    print("开始构建 运维辅助工具 GUI...")

    system = platform.system().lower()
    arch = platform.machine().lower()
    
    if arch in ['x86_64', 'amd64']:
        arch_name = 'x64'
    elif arch in ['arm64', 'aarch64']:
        arch_name = 'arm64'
    else:
        arch_name = arch

    if system == 'windows':
        output_name = f'niuma-windows-{arch_name}'
    elif system == 'linux':
        output_name = f'niuma-linux-{arch_name}'
    elif system == 'darwin':
        output_name = f'niuma-macos-{arch_name}'
    else:
        output_name = f'niuma-{system}-{arch_name}'

    cmd = [
        sys.executable, '-m', 'nuitka',
        '--standalone',
        '--enable-plugins=pyqt5',
        '--include-qt-plugins=platforms,imageformats,iconengines',
        '--follow-imports',
        '--nofollow-import-to=tkinter,matplotlib,pandas,scipy,pytest,doctest',
        '--nofollow-import-to=tests',
        '--nofollow-import-to=PyQt5.QtQuick,PyQt5.QtQuick3D,PyQt5.QtQml,PyQt5.QtQuickWidgets',
        '--include-data-dir=gui/styles=gui/styles',
        '--output-dir=dist',
        f'--output-filename={output_name}',
        '--assume-yes-for-downloads',
        f'--jobs={os.cpu_count()}',
        'main.py'
    ]

    if system == 'windows':
        cmd.append('--windows-console-mode=disable')
        cmd.append('--include-data-file=icons/app.ico=icons/app.ico')
        if os.path.exists('icons/app.ico'):
            cmd.append('--windows-icon-from-ico=icons/app.ico')
    else:
        cmd.append('--file-reference-choice=runtime')
        if os.path.exists('icons/app.png'):
            cmd.append('--linux-icon=icons/app.png')

    print(f"执行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        main_dist = os.path.join('dist', 'main.dist')
        output_dist = os.path.join('dist', output_name)
        
        if os.path.exists(main_dist):
            if os.path.exists(output_dist):
                shutil.rmtree(output_dist)
            shutil.move(main_dist, output_dist)
            print(f"构建成功！输出目录: {output_dist}")
            
            compress_output(output_dist, output_name, system)
        else:
            print(f"构建成功！可执行文件: dist/{output_name}")
    else:
        print("构建失败")
        sys.exit(1)

def compress_output(output_dist, output_name, system):
    print("开始压缩...")
    
    if system == 'windows':
        archive_path = os.path.join('dist', f'{output_name}.7z')
        subprocess.run([
            '7z', 'a', '-t7z', '-mx=9', '-m0=lzma2',
            '-mfb=64', '-md=32m', '-ms=on',
            archive_path, output_name
        ], cwd='dist', check=True)
    else:
        archive_path = os.path.join('dist', f'{output_name}.tar.gz')
        with tarfile.open(archive_path, 'w:gz', compresslevel=9) as tar:
            tar.add(output_dist, arcname=output_name)
    
    archive_size = os.path.getsize(archive_path) / (1024 * 1024)
    print(f"压缩完成: {archive_path} ({archive_size:.2f} MB)")

if __name__ == '__main__':
    build()
