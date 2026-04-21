#!/usr/bin/env python3
import os
import subprocess
import sys
import shutil
import argparse

def run_command(cmd, check=True, shell=False, cwd=None):
    print(f"执行命令: {cmd}")
    if shell:
        result = subprocess.run(cmd, shell=True, check=check, cwd=cwd)
    else:
        result = subprocess.run(cmd, check=check, cwd=cwd)
    return result

def build_in_docker(workspace, docker_image="debian:10.10"):
    print(f"=== 在 Docker 容器 {docker_image} 中执行编译 ===")
    
    docker_cmd = [
        "docker", "run", "--rm",
        "--platform", "linux/arm64",
        "-v", f"{workspace}:/workspace",
        "-w", "/workspace",
        docker_image,
        "bash", "-c",
        """
set -e

echo "=== 配置 apt 源 (Debian 10 已归档) ==="
echo 'deb http://archive.debian.org/debian buster main' > /etc/apt/sources.list
echo 'deb http://archive.debian.org/debian buster-updates main' >> /etc/apt/sources.list
echo 'Acquire::Check-Valid-Until false;' > /etc/apt/apt.conf.d/99no-check-valid-until

echo "=== 安装系统依赖 ==="
apt-get update
apt-get install -y \\
  gcc g++ make wget patchelf \\
  libxrender-dev libxext-dev libx11-dev \\
  libxcb1-dev libxkbcommon-dev \\
  libxcb-* \\
  libgl1-mesa-dev libegl1-mesa-dev \\
  libxkbcommon-x11-dev \\
  libssl-dev \\
  bzip2 libbz2-dev \\
  libffi-dev \\
  zlib1g-dev \\
  liblzma-dev \\
  libsqlite3-dev \\
  libreadline-dev \\
  tk-dev \\
  libgdbm-dev \\
  libxkbcommon-x11-0 \\
  libxcb-cursor0 \\
  libxcb-icccm4 \\
  libxcb-image0 \\
  libxcb-keysyms1 \\
  libxcb-randr0 \\
  libxcb-render-util0 \\
  libxcb-shape0 \\
  libxcb-xfixes0 \\
  libxcb-xinerama0 \\
  libxcb-xkb1

echo "=== 安装 Qt6 构建依赖 ==="
apt-get install -y \\
  ninja-build perl python3 \\
  libgles2-mesa-dev libwayland-dev wayland-protocols \\
  libinput-dev libxkbcommon-dev libdrm-dev \\
  libgbm-dev libasound2-dev libpulse-dev \\
  libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \\
  libfreetype6-dev libfontconfig1-dev \\
  libharfbuzz-dev libjpeg-dev libpng-dev \\
  libstdc++-8-dev

echo "=== 编译 Python 3.12 ==="
cd /tmp
wget -q https://www.python.org/ftp/python/3.12.13/Python-3.12.13.tgz
tar xzf Python-3.12.13.tgz
cd Python-3.12.13
./configure --enable-optimizations --prefix=/usr/local/python3.12
make -j$(nproc)
make install
cd /workspace
/usr/local/python3.12/bin/python3.12 -m pip install --upgrade pip setuptools wheel

echo "=== 安装 CMake 3.30 ==="
cd /tmp
CMAKE_VERSION=3.30.5
wget -q https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-linux-aarch64.tar.gz
tar -xzf cmake-${CMAKE_VERSION}-linux-aarch64.tar.gz
export PATH=/tmp/cmake-${CMAKE_VERSION}-linux-aarch64/bin:$PATH
cmake --version

echo "=== 下载并编译 Qt6 (arm64) ==="
cd /tmp
QT_VERSION=6.5.3
wget -q https://download.qt.io/official_releases/qt/6.5/${QT_VERSION}/single/qt-everywhere-src-${QT_VERSION}.tar.xz
tar -xf qt-everywhere-src-${QT_VERSION}.tar.xz
cd qt-everywhere-src-${QT_VERSION}

mkdir build && cd build
cmake .. \\
  -G "Unix Makefiles" \\
  -DCMAKE_BUILD_TYPE=Release \\
  -DCMAKE_INSTALL_PREFIX=/opt/qt6 \\
  -DCMAKE_CXX_FLAGS="-std=c++17" \\
  -DCMAKE_EXE_LINKER_FLAGS="-lstdc++fs" \\
  -DCMAKE_SHARED_LINKER_FLAGS="-lstdc++fs" \\
  -DCMAKE_MODULE_LINKER_FLAGS="-lstdc++fs" \\
  -DCMAKE_CXX_STANDARD_LIBRARIES="-lstdc++fs" \\
  -DQT_BUILD_EXAMPLES=OFF \\
  -DQT_BUILD_TESTS=OFF \\
  -DQT_FEATURE_vulkan=OFF \\
  -DQT_FEATURE_opengl=ON \\
  -DQT_FEATURE_opengles2=ON \\
  -DQT_FEATURE_egl=ON \\
  -DQT_FEATURE_xcb=ON \\
  -DQT_FEATURE_xcb_xlib=ON \\
  -DQT_FEATURE_xlib=ON

make -j$(nproc)
cmake --install .

export PATH="/opt/qt6/bin:$PATH"
export QT_PLUGIN_PATH="/opt/qt6/plugins"
qmake --version

echo "=== 编译 PyQt6 (arm64) ==="
cd /workspace
export PATH="/usr/local/python3.12/bin:$PATH"
export PYTHONPATH="/usr/local/python3.12/lib/python3.12/site-packages:$PYTHONPATH"
pip3.12 install PyQt6-sip sip html5lib
pip3.12 install --no-binary :all: PyQt6
pip3.12 install --no-binary :all: PyQt6-QScintilla

echo "=== 安装其他依赖 ==="
/usr/local/python3.12/bin/pip3.12 install -r requirements.txt
/usr/local/python3.12/bin/pip3.12 install nuitka ordered-set zstandard

echo "=== 使用 Nuitka 构建 ==="
cd /workspace
/usr/local/python3.12/bin/python3.12 -m nuitka --standalone \\
  --enable-plugins=pyqt6 \\
  --include-qt-plugins=qml,platforms,imageformats,iconengines \\
  --follow-imports \\
  --nofollow-import-to=tkinter,matplotlib,pandas,scipy,pytest,doctest \\
  --nofollow-import-to=tests \\
  --include-data-dir=gui/styles=gui/styles \\
  --output-dir=dist \\
  --output-filename=niuma-linux-arm64 \\
  --assume-yes-for-downloads \\
  --jobs=$(nproc) \\
  --file-reference-choice=runtime \\
  --include-package-data=PyQt6 \\
  --linux-icon=icons/app.png \\
  main.py

echo "=== 验证并打包构建产物 ==="
ls -la dist/
if [ -d "dist/main.dist" ]; then
  mv dist/main.dist dist/niuma-linux-arm64
  cd dist
  tar -I "gzip -9" -cvf niuma-linux-arm64.tar.gz -C niuma-linux-arm64 .
  chown -R 1001:1001 /workspace/dist
  chmod -R 755 /workspace/dist
  echo "构建成功: dist/niuma-linux-arm64.tar.gz"
else
  echo "构建失败: 输出目录未找到"
  exit 1
fi
        """
    ]
    
    run_command(docker_cmd, check=True)

def main():
    parser = argparse.ArgumentParser(description="在 Docker 容器中构建 arm64 版本")
    parser.add_argument("--docker-image", default="debian:10.10", help="Docker 镜像名称 (默认: debian:10.10)")
    parser.add_argument("--no-docker", action="store_true", help="不使用 Docker，直接在当前环境执行")
    
    args = parser.parse_args()
    
    workspace = os.getcwd()
    
    if args.no_docker:
        print("=== 直接在当前环境执行编译 ===")
        print("警告: 此模式需要当前环境为 arm64 架构的 Debian 10.10")
        build_in_docker(workspace, docker_image="")
    else:
        build_in_docker(workspace, docker_image=args.docker_image)

if __name__ == "__main__":
    main()
