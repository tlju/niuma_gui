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
        sep = ';'
    elif system == 'linux':
        output_name = f'niuma-linux-{arch_name}'
        sep = ':'
    elif system == 'darwin':
        output_name = f'niuma-macos-{arch_name}'
        sep = ':'
    else:
        output_name = f'niuma-{system}-{arch_name}'
        sep = ':'

    data_sep = sep

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm',
        '--clean',
        '--distpath', 'dist',
        '--workpath', 'build',
        '--contents-directory', 'bin',
        '--name', output_name,
        '--noconsole',
        '--add-data', f'gui/styles{data_sep}gui/styles',
        '--exclude-module', 'tkinter',
        '--exclude-module', 'matplotlib',
        '--exclude-module', 'pandas',
        '--exclude-module', 'scipy',
        '--exclude-module', 'pytest',
        '--exclude-module', 'doctest',
        '--exclude-module', 'PyQt5.QtQuick',
        '--exclude-module', 'PyQt5.QtQuick3D',
        '--exclude-module', 'PyQt5.QtQml',
        '--exclude-module', 'PyQt5.QtQuickWidgets',
        'main.py'
    ]

    if system == 'windows':
        if os.path.exists('icons/app.ico'):
            cmd.extend(['--icon', 'icons/app.ico'])
            cmd.extend(['--add-data', f'icons/app.ico{data_sep}icons'])
    else:
        if os.path.exists('icons/app.png'):
            cmd.extend(['--icon', 'icons/app.png'])

    print(f"执行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        output_dist = os.path.join('dist', output_name)
        if os.path.exists(output_dist):
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
        if shutil.which('7z'):
            archive_path = os.path.join('dist', f'{output_name}.7z')
            subprocess.run([
                '7z', 'a', '-t7z', '-mx=9', '-m0=lzma2',
                '-mfb=64', '-md=32m', '-ms=on',
                archive_path, output_name
            ], cwd='dist', check=True)
        else:
            archive_path = os.path.join('dist', f'{output_name}.zip')
            print("未找到 7z，使用 zip 格式压缩...")
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                for root, dirs, files in os.walk(output_dist):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, 'dist')
                        zf.write(file_path, arcname)
    else:
        archive_path = os.path.join('dist', f'{output_name}.tar.gz')
        with tarfile.open(archive_path, 'w:gz', compresslevel=9) as tar:
            tar.add(output_dist, arcname=output_name)

    archive_size = os.path.getsize(archive_path) / (1024 * 1024)
    print(f"压缩完成: {archive_path} ({archive_size:.2f} MB)")


if __name__ == '__main__':
    build()
