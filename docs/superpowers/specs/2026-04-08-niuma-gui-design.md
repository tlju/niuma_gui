# 牛马运维辅助系统 - PyQt6 纯 GUI 版本设计文档

## 项目概述

将原 FastAPI + Vue 前后端分离架构改造为 PyQt6 纯 Python 单应用 GUI 项目，支持 x64、arm64 多架构和 Windows/Linux 跨平台。

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                      PyQt6 GUI Layer                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │ 登录窗口 │  │ 主窗口   │  │ 页面组件 │  │ 终端   │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │ Qt Signal/Slot
┌──────────────────────┴──────────────────────────────────┐
│                    Business Logic Layer                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │ 资产服务 │  │ 脚本服务 │  │ 用户服务 │  │ ...    │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│                      Data Access Layer                  │
│              SQLAlchemy ORM / SQLite Database          │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│                     Infrastructure                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Paramiko │  │ Ptyon    │  │ 加密工具 │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
```

### 目录结构

```
niuma_gui/
├── main.py                 # 应用入口
├── models/                 # 数据模型
│   ├── __init__.py
│   ├── user.py
│   ├── server_asset.py
│   ├── script.py
│   ├── exec_log.py
│   ├── audit_log.py
│   └── ...
├── services/               # 业务逻辑层
│   ├── __init__.py
│   ├── auth_service.py
│   ├── asset_service.py
│   ├── script_service.py
│   ├── session_service.py
│   └── ...
├── gui/                    # PyQt6 GUI 层
│   ├── __init__.py
│   ├── main_window.py          # 主窗口
│   ├── login_dialog.py         # 登录对话框
│   ├── pages/                  # 各功能页面
│   │   ├── assets_page.py      # 资产管理
│   │   ├── configs_page.py     # 连接配置
│   │   ├── sessions_page.py    # 会话管理
│   │   ├── scripts_page.py     # 脚本管理
│   │   ├── audit_page.py       # 审计日志
│   │   ├── dicts_page.py       # 数据字典
│   │   ├── params_page.py      # 系统参数
│   │   ├── workflows_page.py   # 工作流
│   │   ├── todos_page.py       # 待办事项
│   │   └── documents_page.py   # 文档管理
│   ├── widgets/                # 自定义控件
│   │   ├── terminal_widget.py  # SSH 终端控件
│   │   ├── code_editor.py      # 代码编辑器
│   │   └── table_widget.py     # 表格控件
│   ├── components/             # 通用组件
│   │   ├── status_bar.py
│   │   └── toast.py
│   └── utils/                  # GUI 工具
│       ├── style.py            # 样式加载
│       └── helpers.py          # 辅助函数
├── core/                   # 核心功能
│   ├── __init__.py
│   ├── database.py            # 数据库管理
│   ├── session_manager.py     # SSH 会话管理
│   ├── ssh_client.py          # SSH 客户端
│   └── config.py              # 配置管理
├── requirements.txt            # Python 依赖
├── pyinstaller.spec           # 打包配置
├── .github/
│   └── workflows/
│       └── build.yml          # CI/CD 工作流
└── README.md
```

## 功能模块设计

### 1. 用户认证模块

**GUI 组件**: `LoginDialog` (QDialog)

**功能**:
- 用户名/密码登录
- 密码加密存储
- 记住密码选项
- Token 会话管理

**服务**: `AuthService`
- `login(username, password) -> bool`
- `logout() -> bool`
- `verify_token(token) -> bool`

### 2. 资产管理模块

**GUI 组件**: `AssetsPage` (QWidget)

**功能**:
- 资产列表展示（表格）
- 添加/编辑/删除资产
- Excel 批量导入
- 搜索过滤

**表格列**: ID、名称、主机名、IP、端口、OS、描述、操作

**服务**: `AssetService`
- `get_all() -> List[Asset]`
- `create(asset) -> Asset`
- `update(asset_id, data) -> bool`
- `delete(asset_id) -> bool`
- `import_from_excel(file_path) -> int`

### 3. 连接配置模块

**GUI 组件**: `ConfigsPage` (QWidget)

**功能**:
- SSH 配置管理
- 密码/私钥认证
- OTP 支持
- 连接测试

**服务**: `ConfigService`
- `get_all() -> List[Config]`
- `create(config) -> Config`
- `update(config_id, data) -> bool`
- `delete(config_id) -> bool`
- `test_connection(config) -> bool`

### 4. 会话管理模块

**GUI 组件**: `SessionsPage` (QWidget) + `TerminalWidget` (QWidget)

**功能**:
- 活动会话列表
- SSH 终端集成
- Tab 页多终端
- 会话关闭

**服务**: `SessionService`
- `get_active_sessions() -> List[Session]`
- `create_session(config_id) -> Session`
- `close_session(session_id) -> bool`

### 5. 终端控件设计

**GUI 组件**: `TerminalWidget` (基于 QPlainTextEdit + Ptyon)

**功能**:
- 伪终端集成 (ptyon)
- ANSI 颜色支持
- 字符输入/输出
- 终端大小调整
- 复制/粘贴

**与 Paramiko 集成**:
```
Paramiko Channel -> Ptyon -> TerminalWidget Display
User Input -> Paramiko Channel
```

### 6. 脚本管理模块

**GUI 组件**: `ScriptsPage` (QWidget) + `CodeEditor` (QPlainTextEdit)

**功能**:
- 脚本 CRUD
- 代码编辑（语法高亮）
- 远程执行
- 执行日志查看

**服务**: `ScriptService`
- `get_all() -> List[Script]`
- `create(script) -> Script`
- `execute(script_id, server_id) -> ExecLog`
- `get_exec_logs(script_id) -> List[ExecLog]`

### 7. 审计日志模块

**GUI 组件**: `AuditPage` (QWidget)

**功能**:
- 审计日志列表
- 时间范围过滤
- 操作类型过滤
- 导出功能

**服务**: `AuditService`
- `get_logs(filters) -> List[AuditLog]`
- `log_action(action_type, resource, details)`

## 数据模型设计

复用原项目的 SQLAlchemy 模型，保持数据库结构一致：

```python
# 栓心模型
- User (用户)
- ServerAsset (服务器资产)
- Script (脚本)
- ExecLog (执行日志)
- AuditLog (审计日志)
- SystemConfig (系统配置)
- DataDict, DataDictItem (数据字典)
- SystemParam (系统参数)
- WorkflowTemplate, WorkflowInstance, WorkflowExecution (工作流)
- Todo (待办)
- Document (文档)
```

## 技术栈

### 核心依赖

```txt
PyQt6                 # GUI 框架
SQLAlchemy>=2.0.0     # ORM
paramiko>=3.0.0       # SSH 客户端
ptyon>=1.0.0          # 伪终端支持
pydantic>=2.0.0        # 数据验证
pydantic-settings     # 配置管理
python-dotenv         # 环境变量
cryptography>=41.0.0  # 加密
bcrypt>=4.0.0          # 密码哈希
openpyxl>=3.1.0       # Excel 读取
xlsxwriter>=3.1.0     # Excel 写入
alembic>=1.12.0       # 数据库迁移
```

### 打包工具

```txt
PyInstaller>=6.0.0    # 应用打包
```

## 跨平台支持

### 架构支持

| 平台 | 架构 | 构建环境 | 产物 |
|------|------|----------|------|
| Linux | x86_64 | Ubuntu 22.04 | `niuma-linux-x64` |
| Linux | arm64 | Ubuntu 22.04 + QEMU | `niuma-linux-arm64` |
| Windows | x86_64 | Windows Server 2022 | `niuma-windows-x64.exe` |

### glibc 兼容性

- 使用 Python 3.10+ (兼容 glibc 2.28+)
- 静态链接关键依赖
- PyInstaller 打包时排除系统依赖

## 打包配置

### PyInstaller 配置要点

```python
# pyinstaller.spec

Data files:
- models/
- services/
- core/
- gui/

Hidden imports:
- 所有应用模块
- PyQt6 插件

Excludes:
- tkinter
- matplotlib
- numpy
- pandas

Single file: True
Console: False
```

## CI/CD 工作流

### GitHub Actions 构建矩阵

```yaml
strategy:
  matrix:
    os: [ubuntu-22.04, windows-2022]
    arch: [x64]
    include:
      - os: ubuntu-22.04
        arch: arm64
        qemu: true
```

### 构建步骤

1. **环境准备** - 安装 Python 和依赖
2. **QEMU 设置** - arm64 交叉编译
3. **依赖安装** - pip install requirements.txt
4. **打包构建** - pyinstaller pyinstaller.spec
5. **产物上传** - 上传到 GitHub
6. **Release 创建** - 有 Tag 时自动发布

## 数据迁移

从原项目迁移数据：

```python
# 迁移脚本
def migrate_database():
    # 读取原项目 niuma.db
    # 导出为 SQL 或 JSON
    # 导入到新数据库
```

## 安全设计

1. **密码加密** - 使用 bcrypt 哈希存储
2. **SSH 凭证加密** - 使用 Fernet 对称加密
3. **数据库加密** - 可选 SQLCipher 支持
4. **审计日志** - 所有操作记录不可篡改

## 性能优化

1. **数据缓存** - QCacheWidget 缓存
2. **异步操作** - QThreadPool 处理耗时任务
3. **分页加载** - 大数据集分页展示
4. **会话超时** - 自动清理闲置会话

## 测试计划

1. **单元测试** - pytest 测试各 Service
2. **GUI 测试** - pytest-qt 测试界面交互
3. **集成测试** - 测试完整业务流程
4. **性能测试** - 压力测试多终端场景

## 实施步骤

1. 搭建项目骨架
2. 实现数据模型和数据库
3. 实现核心业务逻辑 (Services)
4. 实现 GUI 主框架
5. 实现各功能模块
6. 实现 SSH 终端集成
7. 配置打包和 CI/CD
8. 测试和优化

## 版本信息

- 版本: 2.0.0
- 设计日期: 2026-04-08
- 状态: 待实施
