#!/usr/bin/env python3
import os
import subprocess
import sys
import shutil

def run_command(cmd, check=True, shell=False):
    print(f"执行命令: {cmd}")
    if shell:
        result = subprocess.run(cmd, shell=True, check=check)
    else:
        result = subprocess.run(cmd, check=check)
    return result

def main():
    workspace = os.getcwd()
    python_version = "3.12.13"
    cmake_version = "3.30.5"
    qt_version = "6.5.3"
    output_name = "niuma-linux-arm64"
    
    print("=== 配置 apt 源 (Debian 10 已归档) ===")
    run_command("echo 'deb http://archive.debian.org/debian buster main' > /etc/apt/sources.list", shell=True)
    run_command("echo 'deb http://archive.debian.org/debian buster-updates main' >> /etc/apt/sources.list", shell=True)
    run_command("echo 'Acquire::Check-Valid-Until false;' > /etc/apt/apt.conf.d/99no-check-valid-until", shell=True)
    
    print("=== 安装系统依赖 ===")
    run_command("apt-get update", shell=True)
    run_command([
        "apt-get", "install", "-y",
        "gcc", "g++", "make", "wget", "patchelf",
        "libxrender-dev", "libxext-dev", "libx11-dev",
        "libxcb1-dev", "libxkbcommon-dev",
        "libxcb-*",
        "libgl1-mesa-dev", "libegl1-mesa-dev",
        "libxkbcommon-x11-dev",
        "libssl-dev",
        "bzip2", "libbz2-dev",
        "libffi-dev",
        "zlib1g-dev",
        "liblzma-dev",
        "libsqlite3-dev",
        "libreadline-dev",
        "tk-dev",
        "libgdbm-dev",
        "libxkbcommon-x11-0",
        "libxcb-cursor0",
        "libxcb-icccm4",
        "libxcb-image0",
        "libxcb-keysyms1",
        "libxcb-randr0",
        "libxcb-render-util0",
        "libxcb-shape0",
        "libxcb-xfixes0",
        "libxcb-xinerama0",
        "libxcb-xkb1"
    ])
    
    print("=== 安装 Qt6 构建依赖 ===")
    run_command([
        "apt-get", "install", "-y",
        "ninja-build", "perl", "python3",
        "libgles2-mesa-dev", "libwayland-dev", "wayland-protocols",
        "libinput-dev", "libxkbcommon-dev", "libdrm-dev",
        "libgbm-dev", "libasound2-dev", "libpulse-dev",
        "libgstreamer1.0-dev", "libgstreamer-plugins-base1.0-dev",
        "libfreetype6-dev", "libfontconfig1-dev",
        "libharfbuzz-dev", "libjpeg-dev", "libpng-dev",
        "libstdc++-8-dev"
    ])
    
    print("=== 编译 Python 3.12 ===")
    os.chdir("/tmp")
    run_command(f"wget -q https://www.python.org/ftp/python/{python_version}/Python-{python_version}.tgz", shell=True)
    run_command(f"tar xzf Python-{python_version}.tgz", shell=True)
    os.chdir(f"Python-{python_version}")
    run_command(["./configure", "--enable-optimizations", "--prefix=/usr/local/python3.12"])
    run_command(["make", f"-j{os.cpu_count()}"])
    run_command(["make", "install"])
    os.chdir(workspace)
    run_command("/usr/local/python3.12/bin/python3.12 -m pip install --upgrade pip setuptools wheel", shell=True)
    
    print("=== 安装 CMake 3.30 ===")
    os.chdir("/tmp")
    run_command(f"wget -q https://github.com/Kitware/CMake/releases/download/v{cmake_version}/cmake-{cmake_version}-linux-aarch64.tar.gz", shell=True)
    run_command(f"tar -xzf cmake-{cmake_version}-linux-aarch64.tar.gz", shell=True)
    os.environ["PATH"] = f"/tmp/cmake-{cmake_version}-linux-aarch64/bin:{os.environ.get('PATH', '')}"
    run_command("cmake --version", shell=True)
    
    print("=== 下载并编译 Qt6 (arm64) ===")
    os.chdir("/tmp")
    run_command(f"wget -q https://download.qt.io/official_releases/qt/6.5/{qt_version}/single/qt-everywhere-src-{qt_version}.tar.xz", shell=True)
    run_command(f"tar -xf qt-everywhere-src-{qt_version}.tar.xz", shell=True)
    os.chdir(f"qt-everywhere-src-{qt_version}")
    
    os.makedirs("build", exist_ok=True)
    os.chdir("build")
    
    cmake_cmd = [
        "cmake", "..",
        "-G", "Unix Makefiles",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_INSTALL_PREFIX=/opt/qt6",
        "-DCMAKE_CXX_FLAGS=-std=c++17",
        "-DCMAKE_EXE_LINKER_FLAGS=-lstdc++fs",
        "-DCMAKE_SHARED_LINKER_FLAGS=-lstdc++fs",
        "-DCMAKE_MODULE_LINKER_FLAGS=-lstdc++fs",
        "-DCMAKE_CXX_STANDARD_LIBRARIES=-lstdc++fs",
        "-DQT_BUILD_EXAMPLES=OFF",
        "-DQT_BUILD_TESTS=OFF",
        "-DQT_FEATURE_vulkan=OFF",
        "-DQT_FEATURE_opengl=ON",
        "-DQT_FEATURE_opengles2=ON",
        "-DQT_FEATURE_egl=ON",
        "-DQT_FEATURE_xcb=ON",
        "-DQT_FEATURE_xcb_xlib=ON",
        "-DQT_FEATURE_xlib=ON"
    ]
    run_command(cmake_cmd)
    run_command(["make", f"-j{os.cpu_count()}"])
    run_command(["cmake", "--install", "."])
    
    os.environ["PATH"] = "/opt/qt6/bin:" + os.environ.get("PATH", "")
    os.environ["QT_PLUGIN_PATH"] = "/opt/qt6/plugins"
    run_command("qmake --version", shell=True)
    
    print("=== 编译 PyQt6 (arm64) ===")
    os.chdir(workspace)
    os.environ["PATH"] = "/usr/local/python3.12/bin:" + os.environ.get("PATH", "")
    os.environ["PYTHONPATH"] = "/usr/local/python3.12/lib/python3.12/site-packages:" + os.environ.get("PYTHONPATH", "")
    run_command("pip3.12 install PyQt6-sip sip html5lib", shell=True)
    run_command("pip3.12 install --no-binary :all: PyQt6", shell=True)
    run_command("pip3.12 install --no-binary :all: PyQt6-QScintilla", shell=True)
    
    print("=== 安装其他依赖 ===")
    run_command("/usr/local/python3.12/bin/pip3.12 install -r requirements.txt", shell=True)
    run_command("/usr/local/python3.12/bin/pip3.12 install nuitka ordered-set zstandard", shell=True)
    
    print("=== 使用 Nuitka 构建 ===")
    os.chdir(workspace)
    nuitka_cmd = [
        "/usr/local/python3.12/bin/python3.12", "-m", "nuitka", "--standalone",
        "--enable-plugins=pyqt6",
        "--include-qt-plugins=qml,platforms,imageformats,iconengines",
        "--follow-imports",
        "--nofollow-import-to=tkinter,matplotlib,pandas,scipy,pytest,doctest",
        "--nofollow-import-to=tests",
        "--include-data-dir=gui/styles=gui/styles",
        "--output-dir=dist",
        f"--output-filename={output_name}",
        "--assume-yes-for-downloads",
        f"--jobs={os.cpu_count()}",
        "--file-reference-choice=runtime",
        "--include-package-data=PyQt6",
        "--linux-icon=icons/app.png",
        "main.py"
    ]
    run_command(nuitka_cmd)
    
    print("=== 验证并打包构建产物 ===")
    run_command("ls -la dist/", shell=True)
    
    if os.path.exists("dist/main.dist"):
        shutil.move("dist/main.dist", f"dist/{output_name}")
        os.chdir("dist")
        run_command(f"tar -I 'gzip -9' -cvf {output_name}.tar.gz -C {output_name} .", shell=True)
        print(f"构建成功: dist/{output_name}.tar.gz")
    else:
        print("构建失败: 输出目录未找到")
        sys.exit(1)

if __name__ == "__main__":
    main()
