# 运维辅助工具 - GUI 版本

纯 Python GUI 版本，基于 PyQt5 实现，支持 x64/arm64 和 Windows/Linux。

## 功能特性

- 用户认证（登录/注册）
- 服务器资产管理
- 脚本管理和远程执行
- 审计日志查看
- 跨平台支持（Windows/Linux）

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python main.py
```

## 系统要求

- Python 3.10+
- Windows 10+ 或 Linux (glibc 2.28+)

## 构建打包

```bash
# 使用构建脚本
python build.py
```

## GitHub Actions 自动构建

- 推送到 main 分支触发构建
- 创建 Release 触发发布
- 支持多平台（Linux x64/arm64, Windows x64）

## 许可证

MIT License
