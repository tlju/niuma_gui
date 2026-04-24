from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QTextBrowser,
    QPushButton, QSplitter, QFrame, QApplication,
    QSizePolicy, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QBrush, QPen
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet
from core.logger import get_logger

logger = get_logger(__name__)


HELP_DATA = [
    {
        "id": "login",
        "title": "登录系统",
        "icon_func": "user_icon",
        "content": """
<h2>登录系统</h2>
<p>运维辅助工具启动后会首先显示登录界面，用户需要输入用户名和密码进行身份验证。</p>

<h3>功能说明</h3>
<table class="feature-table">
<tr><th>功能</th><th>说明</th></tr>
<tr><td>用户名输入</td><td>输入已注册的系统用户名</td></tr>
<tr><td>密码输入</td><td>输入对应的登录密码，密码输入框默认隐藏字符</td></tr>
<tr><td>登录按钮</td><td>点击进行身份验证，成功后进入主界面</td></tr>
<tr><td>回车登录</td><td>在密码框中按 Enter 键可直接登录</td></tr>
</table>

<h3>操作步骤</h3>
<ol>
<li>启动应用程序，进入登录界面</li>
<li>在"用户名"输入框中输入您的用户名</li>
<li>在"密码"输入框中输入您的密码</li>
<li>点击"登录"按钮或按 Enter 键提交</li>
<li>验证成功后自动跳转到主界面</li>
</ol>

<h3>提示</h3>
<ul>
<li>如果连续多次登录失败，请联系系统管理员</li>
<li>退出系统时会自动记录登出日志</li>
</ul>
"""
    },
    {
        "id": "assets",
        "title": "资产管理",
        "icon_func": "asset_icon",
        "content": """
<h2>资产管理</h2>
<p>资产管理模块用于集中管理服务器资产信息，支持添加、编辑、删除、搜索、导入和导出资产。</p>

<div class="schematic">
<div class="schematic-title">资产管理界面布局</div>
<div class="schematic-row">
<span class="schematic-btn schematic-btn-success">添加资产</span>
<span class="schematic-btn">刷新</span>
<span class="schematic-btn">导出</span>
<span class="schematic-btn">导入</span>
<span class="schematic-filter">单位: [全部 ▾]</span>
<span class="schematic-filter">系统: [全部 ▾]</span>
<span class="schematic-search">🔍 搜索...</span>
</div>
<div class="schematic-table">
<div class="schematic-header">单位 | 系统 | IP地址 | 端口 | 主机名 | 用户名 | 业务服务 | 位置 | 服务器类型 | 操作</div>
<div class="schematic-row-item">示例单位 | 示例系统 | 192.168.1.1 | 22 | server-01 | root | Web服务 | 机房A | 物理机 | <span class="schematic-btn-edit">编辑</span> <span class="schematic-btn-del">删除</span></div>
</div>
</div>

<h3>核心功能</h3>
<table class="feature-table">
<tr><th>功能</th><th>说明</th></tr>
<tr><td>添加资产</td><td>录入新的服务器资产信息，包括IP、主机名、单位、系统等</td></tr>
<tr><td>编辑资产</td><td>修改已有资产的信息</td></tr>
<tr><td>删除资产</td><td>删除指定资产（不可恢复，请谨慎操作）</td></tr>
<tr><td>资产详情</td><td>双击资产行可查看详细信息</td></tr>
<tr><td>筛选过滤</td><td>按单位、系统进行下拉筛选</td></tr>
<tr><td>关键字搜索</td><td>支持按名称、IP、主机名等多字段模糊搜索</td></tr>
<tr><td>导出资产</td><td>将资产列表导出为 Excel 文件</td></tr>
<tr><td>导入资产</td><td>从 Excel 文件批量导入资产数据</td></tr>
</table>

<h3>操作步骤 — 添加资产</h3>
<ol>
<li>点击工具栏"添加资产"按钮</li>
<li>在弹出的对话框中填写资产信息：
    <ul>
    <li>单位：选择资产所属单位（来源数据字典）</li>
    <li>系统：选择所属系统（来源数据字典）</li>
    <li>IP地址：填写服务器IPv4地址</li>
    <li>IPv6：填写服务器IPv6地址（可选）</li>
    <li>端口：填写SSH端口号，默认22</li>
    <li>主机名：填写服务器主机名</li>
    <li>用户名：填写SSH登录用户名</li>
    <li>业务服务：描述该服务器运行的业务</li>
    <li>位置：选择服务器所在位置（来源数据字典）</li>
    <li>服务器类型：选择服务器类型（来源数据字典）</li>
    </ul>
</li>
<li>点击"确定"保存</li>
</ol>

<h3>操作步骤 — 导入导出</h3>
<ol>
<li><b>导出：</b>点击"导出"按钮，选择保存路径，系统将生成 Excel 文件</li>
<li><b>导入：</b>点击"导入"按钮，选择 Excel 文件，系统将批量导入数据</li>
</ol>

<h3>提示</h3>
<ul>
<li>单位、系统、位置、服务器类型的选项来自"数据字典"，需先在数据字典中配置</li>
<li>双击表格行可快速查看资产详情</li>
<li>搜索支持多字段模糊匹配，输入关键词即可实时过滤</li>
</ul>
"""
    },
    {
        "id": "scripts",
        "title": "脚本管理",
        "icon_func": "script_icon",
        "content": """
<h2>脚本管理</h2>
<p>脚本管理模块用于创建、编辑和管理自动化运维脚本，支持多种脚本语言，可在线编辑代码并关联到工作流节点。</p>

<div class="schematic">
<div class="schematic-title">脚本管理界面布局</div>
<div class="schematic-row">
<span class="schematic-btn schematic-btn-success">添加脚本</span>
<span class="schematic-btn">刷新</span>
</div>
<div class="schematic-table">
<div class="schematic-header">ID | 名称 | 描述 | 语言 | 操作</div>
<div class="schematic-row-item">1 | 磁盘检查 | 检查磁盘使用率 | Bash | <span class="schematic-btn-edit">编辑</span> <span class="schematic-btn-del">删除</span> <span class="schematic-btn-run">执行</span></div>
</div>
</div>

<h3>核心功能</h3>
<table class="feature-table">
<tr><th>功能</th><th>说明</th></tr>
<tr><td>添加脚本</td><td>创建新脚本，指定名称、描述、语言和代码内容</td></tr>
<tr><td>编辑脚本</td><td>修改已有脚本的名称、描述或代码</td></tr>
<tr><td>删除脚本</td><td>删除指定脚本</td></tr>
<tr><td>在线编辑</td><td>使用内置代码编辑器编辑脚本，支持语法高亮</td></tr>
<tr><td>执行脚本</td><td>直接在脚本管理页面执行脚本并查看输出</td></tr>
<tr><td>脚本详情</td><td>双击脚本行查看详细信息</td></tr>
</table>

<h3>支持的脚本语言</h3>
<ul>
<li><b>Bash</b> — Shell 脚本，最常用的运维脚本语言</li>
<li><b>Python</b> — Python 脚本，适合复杂的自动化任务</li>
<li><b>SQL</b> — 数据库查询脚本，用于数据操作</li>
</ul>

<h3>操作步骤 — 创建脚本</h3>
<ol>
<li>点击"添加脚本"按钮</li>
<li>填写脚本名称和描述</li>
<li>选择脚本语言（Bash/Python/SQL）</li>
<li>在代码编辑器中编写脚本代码</li>
<li>点击"确定"保存</li>
</ol>

<h3>操作步骤 — 执行脚本</h3>
<ol>
<li>在脚本列表中找到目标脚本</li>
<li>点击操作列中的"执行"按钮</li>
<li>在弹出窗口中查看执行结果和输出</li>
</ol>

<h3>提示</h3>
<ul>
<li>脚本语言选项来自数据字典中的"script_language"</li>
<li>脚本可被工作流中的"脚本执行"节点引用</li>
<li>代码编辑器支持行号显示和等宽字体</li>
</ul>
"""
    },
    {
        "id": "todos",
        "title": "待办事项",
        "icon_func": "todo_icon",
        "content": """
<h2>待办事项</h2>
<p>待办事项模块帮助您管理和跟踪日常工作任务，支持优先级设置、截止日期和循环提醒。</p>

<div class="schematic">
<div class="schematic-title">待办事项界面布局</div>
<div class="schematic-row">
<span class="schematic-btn schematic-btn-success">添加待办</span>
<span class="schematic-btn">刷新</span>
<span class="schematic-filter">状态: [全部 ▾]</span>
</div>
<div class="schematic-table">
<div class="schematic-header">ID | 标题 | 描述 | 状态 | 优先级 | 截止日期 | 循环 | 操作</div>
<div class="schematic-row-item">1 | 系统巡检 | 每日巡检 | <span style="color:#f39c12">待处理</span> | 8 | 2026-04-25 | 每日 | <span class="schematic-btn-complete">完成</span> <span class="schematic-btn-edit">编辑</span> <span class="schematic-btn-del">删除</span></div>
</div>
</div>

<h3>核心功能</h3>
<table class="feature-table">
<tr><th>功能</th><th>说明</th></tr>
<tr><td>添加待办</td><td>创建新的待办事项</td></tr>
<tr><td>编辑待办</td><td>修改已有待办事项的信息</td></tr>
<tr><td>完成待办</td><td>将待办标记为已完成</td></tr>
<tr><td>删除待办</td><td>删除指定待办事项</td></tr>
<tr><td>状态筛选</td><td>按待处理/进行中/已完成筛选</td></tr>
<tr><td>循环设置</td><td>支持每日/每周/每月循环，可设置间隔</td></tr>
</table>

<h3>待办状态说明</h3>
<ul>
<li><span style="color:#f39c12;font-weight:bold">待处理</span> — 新创建的任务，等待开始</li>
<li><span style="color:#3498db;font-weight:bold">进行中</span> — 正在处理的任务</li>
<li><span style="color:#27ae60;font-weight:bold">已完成</span> — 已完成的任务</li>
</ul>

<h3>操作步骤 — 添加待办</h3>
<ol>
<li>点击"添加待办"按钮</li>
<li>填写待办信息：
    <ul>
    <li>标题：待办事项的名称</li>
    <li>描述：详细说明（可选）</li>
    <li>状态：待处理/进行中/已完成</li>
    <li>优先级：1-10，数字越大优先级越高</li>
    <li>截止日期：设置任务截止时间</li>
    <li>循环：选择循环类型和间隔</li>
    </ul>
</li>
<li>点击"确定"保存</li>
</ol>

<h3>循环待办说明</h3>
<p>循环待办完成后，系统会根据循环设置自动创建下一个待办：</p>
<ul>
<li><b>每日</b> — 每天自动创建，可设置间隔（如每2天）</li>
<li><b>每周</b> — 每周自动创建，可设置间隔（如每2周）</li>
<li><b>每月</b> — 每月自动创建，可设置间隔（如每3月）</li>
</ul>
"""
    },
    {
        "id": "documents",
        "title": "文档管理",
        "icon_func": "document_icon",
        "content": """
<h2>文档管理</h2>
<p>文档管理模块用于创建和管理运维文档，支持富文本编辑、分类管理和标签系统。</p>

<div class="schematic">
<div class="schematic-title">文档管理界面布局</div>
<div class="schematic-row">
<span class="schematic-btn schematic-btn-success">添加文档</span>
<span class="schematic-btn">刷新</span>
<span class="schematic-filter">分类: [全部 ▾]</span>
<span class="schematic-search">🔍 搜索标题或内容...</span>
</div>
<div class="schematic-table">
<div class="schematic-header">ID | 标题 | 分类 | 标签 | 创建时间 | 操作</div>
<div class="schematic-row-item">1 | 部署手册 | 技术文档 | 部署,运维 | 2026-04-24 | <span class="schematic-btn-view">查看</span> <span class="schematic-btn-edit">编辑</span> <span class="schematic-btn-del">删除</span></div>
</div>
</div>

<h3>核心功能</h3>
<table class="feature-table">
<tr><th>功能</th><th>说明</th></tr>
<tr><td>添加文档</td><td>创建新文档，支持富文本编辑器</td></tr>
<tr><td>查看文档</td><td>以只读模式查看文档内容</td></tr>
<tr><td>编辑文档</td><td>修改已有文档的标题、分类、标签和内容</td></tr>
<tr><td>删除文档</td><td>删除指定文档</td></tr>
<tr><td>分类筛选</td><td>按文档分类下拉筛选</td></tr>
<tr><td>关键字搜索</td><td>按标题或内容关键字搜索</td></tr>
</table>

<h3>操作步骤 — 创建文档</h3>
<ol>
<li>点击"添加文档"按钮</li>
<li>填写文档信息：
    <ul>
    <li>标题：文档标题</li>
    <li>分类：如"技术文档"、"操作手册"等</li>
    <li>标签：多个标签用逗号分隔</li>
    <li>内容：使用富文本编辑器编写文档内容</li>
    </ul>
</li>
<li>点击"确定"保存</li>
</ol>

<h3>富文本编辑器功能</h3>
<ul>
<li>支持加粗、斜体、下划线等文字格式</li>
<li>支持标题、列表、对齐等段落格式</li>
<li>支持文字颜色和背景色设置</li>
<li>支持插入链接和图片</li>
</ul>
"""
    },
    {
        "id": "workflow",
        "title": "工作流",
        "icon_func": "execute_icon",
        "content": """
<h2>工作流</h2>
<p>工作流模块是核心自动化引擎，通过可视化画布设计运维流程，支持多种节点类型和并行执行。</p>

<div class="schematic">
<div class="schematic-title">工作流设计器布局</div>
<div class="schematic-row">
<span class="schematic-btn schematic-btn-success">新建工作流</span>
<span class="schematic-btn">刷新</span>
</div>
<div class="schematic-layout">
<div class="schematic-palette">
<div class="schematic-palette-title">节点面板</div>
<div class="schematic-palette-item">▶ 开始</div>
<div class="schematic-palette-item">⏹ 结束</div>
<div class="schematic-palette-item">⌨ 命令执行</div>
<div class="schematic-palette-item">📜 脚本执行</div>
<div class="schematic-palette-item">⏱ 延时</div>
<div class="schematic-palette-item">❓ 条件判断</div>
<div class="schematic-palette-item">⇉ 并行执行</div>
<div class="schematic-palette-item">⇉ 合并</div>
<div class="schematic-palette-item">📦 MinIO操作</div>
</div>
<div class="schematic-canvas">
<div class="schematic-canvas-text">可视化画布区域<br>拖拽节点 → 连线 → 执行</div>
</div>
</div>
</div>

<h3>节点类型说明</h3>
<table class="feature-table">
<tr><th>节点</th><th>分类</th><th>说明</th></tr>
<tr><td>开始</td><td>控制</td><td>工作流起始节点，每个工作流必须有一个</td></tr>
<tr><td>结束</td><td>控制</td><td>工作流结束节点</td></tr>
<tr><td>命令执行</td><td>动作</td><td>执行Shell命令，支持变量替换(@dict.xxx / @param.xxx)</td></tr>
<tr><td>脚本执行</td><td>动作</td><td>引用脚本管理中的脚本执行</td></tr>
<tr><td>延时</td><td>控制</td><td>等待指定秒数后继续</td></tr>
<tr><td>条件判断</td><td>控制</td><td>根据Python表达式结果选择分支，有2个输出端口</td></tr>
<tr><td>并行执行</td><td>控制</td><td>同时启动多个并行分支</td></tr>
<tr><td>合并</td><td>控制</td><td>等待多个分支完成后再继续</td></tr>
<tr><td>MinIO操作</td><td>动作</td><td>执行MinIO对象存储操作（上传/下载/删除等）</td></tr>
</table>

<h3>操作步骤 — 创建工作流</h3>
<ol>
<li>点击"新建工作流"按钮</li>
<li>输入工作流名称和描述</li>
<li>从左侧节点面板拖拽节点到画布</li>
<li>双击节点配置参数</li>
<li>在节点端口间拖拽连线建立执行顺序</li>
<li>保存工作流</li>
</ol>

<h3>操作步骤 — 执行工作流</h3>
<ol>
<li>在工作流列表中选择目标工作流</li>
<li>点击"执行"按钮</li>
<li>在执行详情窗口中查看：
    <ul>
    <li><b>执行日志</b> — 实时查看执行过程日志</li>
    <li><b>节点执行</b> — 查看每个节点的执行状态和结果</li>
    <li><b>完整输出</b> — 查看所有节点的输出汇总</li>
    <li><b>错误信息</b> — 执行失败时查看错误详情</li>
    </ul>
</li>
</ol>

<h3>变量替换</h3>
<p>命令执行和脚本执行节点支持变量替换：</p>
<ul>
<li><b>@dict.字典代码.字典项名称</b> — 替换为数据字典项的代码值</li>
<li><b>@param.参数代码</b> — 替换为系统参数的值</li>
<li><b>${input}</b> — 替换为上游节点的输出</li>
</ul>
"""
    },
    {
        "id": "audit",
        "title": "审计日志",
        "icon_func": "audit_icon",
        "content": """
<h2>审计日志</h2>
<p>审计日志模块记录系统中所有用户操作，支持按操作类型筛选和查看详细日志。</p>

<div class="schematic">
<div class="schematic-title">审计日志界面布局</div>
<div class="schematic-row">
<span class="schematic-filter">操作类型: [全部 ▾]</span>
<span class="schematic-btn">刷新</span>
</div>
<div class="schematic-table">
<div class="schematic-header">操作类型 | 详情 | 时间</div>
<div class="schematic-row-item">登录 | 用户admin登录系统 | 2026-04-24 10:00:00</div>
</div>
</div>

<h3>操作类型说明</h3>
<table class="feature-table">
<tr><th>类型</th><th>说明</th></tr>
<tr><td>登录</td><td>用户登录系统的记录</td></tr>
<tr><td>登出</td><td>用户退出系统的记录</td></tr>
<tr><td>创建</td><td>新增数据的操作记录</td></tr>
<tr><td>更新</td><td>修改数据的操作记录</td></tr>
<tr><td>删除</td><td>删除数据的操作记录</td></tr>
<tr><td>执行</td><td>执行脚本或工作流的记录</td></tr>
</table>

<h3>操作步骤</h3>
<ol>
<li>通过"操作类型"下拉框筛选特定类型的日志</li>
<li>点击"刷新"按钮加载最新日志</li>
<li>在表格中查看操作详情和时间</li>
</ol>

<h3>提示</h3>
<ul>
<li>审计日志为只读，不可编辑或删除</li>
<li>所有操作都会被自动记录，确保操作可追溯</li>
</ul>
"""
    },
    {
        "id": "params",
        "title": "系统参数",
        "icon_func": "settings_icon",
        "content": """
<h2>系统参数</h2>
<p>系统参数模块用于管理应用配置项，如堡垒机连接参数、MinIO配置等，参数可在工作流中通过 @param.参数代码 引用。</p>

<div class="schematic">
<div class="schematic-title">系统参数界面布局</div>
<div class="schematic-row">
<span class="schematic-btn schematic-btn-success">添加参数</span>
<span class="schematic-btn">刷新</span>
<span class="schematic-search">🔍 搜索参数...</span>
</div>
<div class="schematic-table">
<div class="schematic-header">参数名称 | 参数代码 | 参数值 | 状态 | 描述 | 操作</div>
<div class="schematic-row-item">堡垒机地址 | BASTION_HOST | 10.0.0.1 | 启用 | 堡垒机IP | <span class="schematic-btn-edit">编辑</span> <span class="schematic-btn-del">删除</span></div>
</div>
</div>

<h3>核心功能</h3>
<table class="feature-table">
<tr><th>功能</th><th>说明</th></tr>
<tr><td>添加参数</td><td>创建新的系统配置参数</td></tr>
<tr><td>编辑参数</td><td>修改参数值、名称或描述</td></tr>
<tr><td>删除参数</td><td>删除指定参数</td></tr>
<tr><td>启用/禁用</td><td>切换参数的启用状态</td></tr>
<tr><td>搜索参数</td><td>按名称、代码或描述搜索</td></tr>
</table>

<h3>常用系统参数</h3>
<table class="feature-table">
<tr><th>参数代码</th><th>说明</th></tr>
<tr><td>BASTION_HOST</td><td>堡垒机地址</td></tr>
<tr><td>BASTION_USER</td><td>堡垒机用户名</td></tr>
<tr><td>BASTION_PASSWORD</td><td>堡垒机密码</td></tr>
<tr><td>MINIO_ENDPOINT</td><td>MinIO服务地址</td></tr>
<tr><td>MINIO_ACCESS_KEY</td><td>MinIO访问密钥</td></tr>
<tr><td>MINIO_SECRET_KEY</td><td>MinIO密钥</td></tr>
<tr><td>MINIO_BUCKET</td><td>MinIO存储桶名称</td></tr>
</table>

<h3>操作步骤 — 添加参数</h3>
<ol>
<li>点击"添加参数"按钮</li>
<li>填写参数信息：
    <ul>
    <li>参数名称：可读的参数名称</li>
    <li>参数代码：唯一标识符，用于工作流引用（如 @param.BASTION_HOST）</li>
    <li>参数值：参数的实际值</li>
    <li>状态：启用/禁用</li>
    <li>描述：参数用途说明</li>
    </ul>
</li>
<li>点击"确定"保存</li>
</ol>
"""
    },
    {
        "id": "dicts",
        "title": "数据字典",
        "icon_func": "dict_icon",
        "content": """
<h2>数据字典</h2>
<p>数据字典模块管理系统中的枚举数据，为其他模块提供下拉选项数据源。字典由字典和字典项两级结构组成。</p>

<div class="schematic">
<div class="schematic-title">数据字典界面布局</div>
<div class="schematic-row">
<span class="schematic-btn schematic-btn-success">添加字典</span>
<span class="schematic-btn schematic-btn-success">添加字典项</span>
<span class="schematic-btn">刷新</span>
</div>
<div class="schematic-layout">
<div class="schematic-table-half">
<div class="schematic-header">代码 | 名称 | 描述 | 操作</div>
<div class="schematic-row-item">unit | 单位 | 资产单位 | <span class="schematic-btn-edit">编辑</span> <span class="schematic-btn-del">删除</span></div>
</div>
<div class="schematic-table-half">
<div class="schematic-header">字典项代码 | 名称 | 值 | 排序 | 操作</div>
<div class="schematic-row-item">company_a | A公司 | - | 1 | <span class="schematic-btn-edit">编辑</span> <span class="schematic-btn-del">删除</span></div>
</div>
</div>
</div>

<h3>核心功能</h3>
<table class="feature-table">
<tr><th>功能</th><th>说明</th></tr>
<tr><td>添加字典</td><td>创建新的字典分类</td></tr>
<tr><td>添加字典项</td><td>在选中的字典下添加字典项</td></tr>
<tr><td>编辑/删除</td><td>修改或删除字典及字典项</td></tr>
</table>

<h3>系统内置字典</h3>
<table class="feature-table">
<tr><th>字典代码</th><th>说明</th><th>使用位置</th></tr>
<tr><td>unit</td><td>资产单位</td><td>资产管理-单位筛选</td></tr>
<tr><td>system</td><td>所属系统</td><td>资产管理-系统筛选</td></tr>
<tr><td>location</td><td>服务器位置</td><td>资产管理-位置字段</td></tr>
<tr><td>server_type</td><td>服务器类型</td><td>资产管理-类型字段</td></tr>
<tr><td>script_language</td><td>脚本语言</td><td>脚本管理-语言选项</td></tr>
</table>

<h3>操作步骤</h3>
<ol>
<li>在左侧"字典"选项卡中选择一个字典</li>
<li>在右侧"字典项"选项卡中查看和编辑该字典下的项</li>
<li>点击"添加字典项"为当前选中的字典添加新项</li>
<li>字典项的"代码"用于系统内部引用，"名称"用于界面显示</li>
</ol>
"""
    },
    {
        "id": "bastion",
        "title": "堡垒机连接",
        "icon_func": "app_icon",
        "content": """
<h2>堡垒机连接</h2>
<p>堡垒机连接功能集成在状态栏中，支持自动登录、二次认证和连接状态管理。</p>

<div class="schematic">
<div class="schematic-title">堡垒机状态指示器（状态栏）</div>
<div class="schematic-row">
<span class="schematic-status schematic-status-disconnected">⬤ 未配置</span>
<span class="schematic-status schematic-status-connecting">⬤ 连接中</span>
<span class="schematic-status schematic-status-authenticated">⬤ 已连接</span>
<span class="schematic-status schematic-status-failed">⬤ 连接失败</span>
</div>
</div>

<h3>连接状态说明</h3>
<table class="feature-table">
<tr><th>状态</th><th>颜色</th><th>说明</th></tr>
<tr><td>未配置</td><td style="color:#95a5a6">灰色</td><td>尚未配置堡垒机参数</td></tr>
<tr><td>连接中</td><td style="color:#f39c12">黄色</td><td>正在建立连接</td></tr>
<tr><td>认证中</td><td style="color:#f39c12">黄色</td><td>正在进行二次认证</td></tr>
<tr><td>已连接</td><td style="color:#27ae60">绿色</td><td>连接成功，可以使用</td></tr>
<tr><td>连接失败</td><td style="color:#e74c3c">红色</td><td>连接失败，请检查配置</td></tr>
</table>

<h3>操作步骤 — 配置堡垒机</h3>
<ol>
<li>在"系统参数"页面添加以下参数：
    <ul>
    <li>BASTION_HOST — 堡垒机地址</li>
    <li>BASTION_USER — 堡垒机用户名</li>
    <li>BASTION_PASSWORD — 堡垒机密码</li>
    </ul>
</li>
<li>配置完成后系统会自动尝试连接</li>
</ol>

<h3>操作步骤 — 手动连接</h3>
<ol>
<li>点击状态栏中的堡垒机状态指示器</li>
<li>选择"连接堡垒机"</li>
<li>如需二次认证，在弹出对话框中输入OTP验证码</li>
</ol>

<h3>操作步骤 — 断开连接</h3>
<ol>
<li>点击状态栏中的堡垒机状态指示器</li>
<li>选择"断开连接"</li>
<li>确认断开</li>
</ol>

<h3>提示</h3>
<ul>
<li>系统启动时会自动检测堡垒机配置并尝试连接</li>
<li>连接失败后会自动重试（最多3次）</li>
<li>二次认证最多可重试3次，超过后需重新连接</li>
</ul>
"""
    },
    {
        "id": "faq",
        "title": "常见问题",
        "icon_func": "about_icon",
        "content": """
<h2>常见问题 (FAQ)</h2>

<h3 class="faq-question">Q: 如何添加新的服务器资产？</h3>
<p>A: 进入"功能 → 资产管理"页面，点击工具栏中的"添加资产"按钮，在弹出的对话框中填写服务器信息后点击"确定"即可。资产的单位、系统、位置等选项来自数据字典，需先在"系统 → 数据字典"中配置。</p>

<h3 class="faq-question">Q: 如何批量导入资产？</h3>
<p>A: 在资产管理页面点击"导入"按钮，选择准备好的 Excel 文件。建议先使用"导出"功能获取模板，按照模板格式填写数据后再导入。</p>

<h3 class="faq-question">Q: 工作流中的变量替换怎么用？</h3>
<p>A: 在命令执行或脚本执行节点的命令/脚本中使用以下语法：<br>
• <code>@dict.字典代码.字典项名称</code> — 替换为数据字典项的代码值<br>
• <code>@param.参数代码</code> — 替换为系统参数的值<br>
• <code>${input}</code> — 替换为上游节点的输出</p>

<h3 class="faq-question">Q: 堡垒机连接失败怎么办？</h3>
<p>A: 请按以下步骤排查：<br>
1. 检查"系统参数"中 BASTION_HOST、BASTION_USER、BASTION_PASSWORD 是否配置正确<br>
2. 确认网络可以访问堡垒机地址<br>
3. 如果需要二次认证，确保输入了正确的OTP验证码<br>
4. 查看状态栏中的错误提示信息</p>

<h3 class="faq-question">Q: 如何创建循环待办？</h3>
<p>A: 在添加或编辑待办时，设置"循环"选项（每日/每周/每月），并设置间隔数。待办完成后，系统会根据循环设置自动创建下一个待办。</p>

<h3 class="faq-question">Q: 数据字典的字典代码有什么用？</h3>
<p>A: 字典代码是系统内部引用字典的标识符。例如，资产管理页面的"单位"下拉框使用"unit"字典，"系统"下拉框使用"system"字典。工作流变量替换中也使用字典代码（如 @dict.unit.某单位）。</p>

<h3 class="faq-question">Q: 工作流执行失败如何排查？</h3>
<p>A: 点击执行记录的"查看详情"，在执行详情窗口中：<br>
1. 查看"执行日志"选项卡了解整体执行过程<br>
2. 查看"节点执行"选项卡定位失败的节点<br>
3. 查看失败节点的错误信息<br>
4. 常见原因包括：命令执行超时、脚本语法错误、变量替换失败等</p>

<h3 class="faq-question">Q: 如何在工作流中使用MinIO？</h3>
<p>A: 在工作流画布中添加"MinIO操作"节点，配置操作类型（上传/下载/删除等）和相关参数。MinIO的连接信息从"系统参数"中读取（MINIO_ENDPOINT、MINIO_ACCESS_KEY、MINIO_SECRET_KEY、MINIO_BUCKET）。</p>

<h3 class="faq-question">Q: 快捷键有哪些？</h3>
<p>A: 系统菜单提供的快捷键：<br>
• <code>Ctrl+U</code> — 审计日志<br>
• <code>Ctrl+P</code> — 系统参数<br>
• <code>Ctrl+D</code> — 数据字典<br>
• <code>Ctrl+A</code> — 资产管理<br>
• <code>Ctrl+S</code> — 脚本管理<br>
• <code>Ctrl+T</code> — 待办事项<br>
• <code>Ctrl+W</code> — 文档管理<br>
• <code>Ctrl+L</code> — 工作流<br>
• <code>Ctrl+Q</code> — 退出系统</p>
"""
    }
]


class HelpPage(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("帮助 - 运维辅助工具")
        self.setMinimumSize(900, 600)
        self.resize(1100, 750)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._all_items = []
        self.init_ui()

    def init_ui(self):
        load_combined_stylesheet(QApplication.instance(), ["common", "help_page"])

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header_frame = QFrame()
        header_frame.setObjectName("helpHeader")
        header_frame.setFixedHeight(60)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 10, 20, 10)

        back_btn = QPushButton("← 返回")
        back_btn.setObjectName("helpBackBtn")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.close)
        header_layout.addWidget(back_btn)

        title_label = QLabel("功能说明")
        title_label.setObjectName("helpTitleLabel")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setObjectName("helpSearchInput")
        self.search_input.setPlaceholderText("搜索帮助内容...")
        self.search_input.setFixedWidth(280)
        self.search_input.setFixedHeight(36)
        self.search_input.textChanged.connect(self._on_search)
        header_layout.addWidget(self.search_input)

        main_layout.addWidget(header_frame)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("helpSplitter")

        sidebar_frame = QFrame()
        sidebar_frame.setObjectName("helpSidebar")
        sidebar_layout = QVBoxLayout(sidebar_frame)
        sidebar_layout.setContentsMargins(8, 8, 8, 8)
        sidebar_layout.setSpacing(4)

        sidebar_title = QLabel("目录")
        sidebar_title.setObjectName("helpSidebarTitle")
        sidebar_layout.addWidget(sidebar_title)

        self.sidebar_list = QListWidget()
        self.sidebar_list.setObjectName("helpSidebarList")
        self.sidebar_list.currentRowChanged.connect(self._on_sidebar_click)
        sidebar_layout.addWidget(self.sidebar_list)

        splitter.addWidget(sidebar_frame)

        content_frame = QFrame()
        content_frame.setObjectName("helpContentFrame")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("helpScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content_browser = QTextBrowser()
        self.content_browser.setObjectName("helpContentBrowser")
        self.content_browser.setOpenExternalLinks(False)

        scroll_area.setWidget(self.content_browser)
        content_layout.addWidget(scroll_area)

        splitter.addWidget(content_frame)

        splitter.setSizes([240, 860])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        self._populate_sidebar()
        if self.sidebar_list.count() > 0:
            self.sidebar_list.setCurrentRow(0)

    def _populate_sidebar(self, filter_text=""):
        self.sidebar_list.clear()
        self._all_items = []

        for section in HELP_DATA:
            if filter_text:
                title_match = filter_text.lower() in section["title"].lower()
                content_match = filter_text.lower() in section["content"].lower()
                if not title_match and not content_match:
                    continue

            icon_func = getattr(icons, section["icon_func"], None)
            icon = icon_func() if icon_func else QIcon()

            item = QListWidgetItem(icon, section["title"])
            item.setData(Qt.UserRole, section["id"])
            item.setSizeHint(QSize(0, 38))
            self.sidebar_list.addItem(item)
            self._all_items.append(section)

    def _on_sidebar_click(self, row):
        if row < 0 or row >= len(self._all_items):
            return

        section = self._all_items[row]
        html_content = self._build_html(section)
        self.content_browser.setHtml(html_content)

    def _on_search(self, text):
        self._populate_sidebar(text.strip())
        if self.sidebar_list.count() > 0:
            self.sidebar_list.setCurrentRow(0)
        else:
            self.content_browser.setHtml(
                "<div style='text-align:center;padding:60px;color:#95a5a6;'>"
                "<h2>未找到相关内容</h2>"
                "<p>请尝试使用其他关键词搜索</p>"
                "</div>"
            )

    def _build_html(self, section):
        base_style = """
            body {
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                font-size: 14px;
                color: #2c3e50;
                line-height: 1.8;
                padding: 24px 28px;
                margin: 0;
            }
            h2 {
                color: #2c3e50;
                font-size: 22px;
                font-weight: 700;
                border-bottom: 2px solid #1abc9c;
                padding-bottom: 10px;
                margin-bottom: 16px;
            }
            h3 {
                color: #34495e;
                font-size: 16px;
                font-weight: 600;
                margin-top: 24px;
                margin-bottom: 10px;
                padding-left: 10px;
                border-left: 3px solid #3498db;
            }
            h3.faq-question {
                color: #8e44ad;
                border-left-color: #8e44ad;
                margin-top: 20px;
            }
            p {
                margin: 8px 0;
            }
            ul, ol {
                margin: 8px 0;
                padding-left: 24px;
            }
            li {
                margin: 4px 0;
            }
            table.feature-table {
                width: 100%;
                border-collapse: collapse;
                margin: 12px 0;
                font-size: 13px;
            }
            table.feature-table th {
                background-color: #34495e;
                color: #ecf0f1;
                padding: 10px 12px;
                text-align: left;
                font-weight: 600;
                border: 1px solid #2c3e50;
            }
            table.feature-table td {
                padding: 8px 12px;
                border: 1px solid #dee2e6;
                vertical-align: top;
            }
            table.feature-table tr:nth-child(even) td {
                background-color: #f8f9fa;
            }
            table.feature-table tr:hover td {
                background-color: #d6eaf8;
            }
            code {
                background-color: #eef;
                color: #c7254e;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 13px;
            }
            b {
                font-weight: 600;
                color: #2c3e50;
            }
            div.schematic {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 16px;
                margin: 16px 0;
            }
            div.schematic-title {
                font-weight: 700;
                color: #2c3e50;
                margin-bottom: 12px;
                font-size: 13px;
            }
            div.schematic-row {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                align-items: center;
                margin-bottom: 8px;
            }
            span.schematic-btn {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
                background-color: #3498db;
                color: #fff;
            }
            span.schematic-btn-success {
                background-color: #27ae60;
            }
            span.schematic-btn-edit {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 11px;
                font-weight: 600;
                background-color: #3498db;
                color: #fff;
            }
            span.schematic-btn-del {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 11px;
                font-weight: 600;
                background-color: #e74c3c;
                color: #fff;
            }
            span.schematic-btn-run {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 11px;
                font-weight: 600;
                background-color: #8e44ad;
                color: #fff;
            }
            span.schematic-btn-view {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 11px;
                font-weight: 600;
                background-color: #1abc9c;
                color: #fff;
            }
            span.schematic-btn-complete {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 11px;
                font-weight: 600;
                background-color: #27ae60;
                color: #fff;
            }
            span.schematic-filter {
                display: inline-block;
                padding: 4px 10px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                font-size: 12px;
                background-color: #fff;
                color: #495057;
            }
            span.schematic-search {
                display: inline-block;
                padding: 4px 10px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                font-size: 12px;
                background-color: #fff;
                color: #adb5bd;
            }
            div.schematic-table {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                overflow: hidden;
            }
            div.schematic-header {
                background-color: #34495e;
                color: #ecf0f1;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 700;
            }
            div.schematic-row-item {
                padding: 6px 12px;
                font-size: 12px;
                border-top: 1px solid #e9ecef;
                background-color: #fff;
            }
            div.schematic-layout {
                display: flex;
                gap: 12px;
                margin-top: 8px;
            }
            div.schematic-palette {
                width: 140px;
                background-color: #fff;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                flex-shrink: 0;
            }
            div.schematic-palette-title {
                font-weight: 700;
                font-size: 12px;
                color: #2c3e50;
                margin-bottom: 6px;
            }
            div.schematic-palette-item {
                padding: 4px 8px;
                font-size: 11px;
                background-color: #e9ecef;
                border-radius: 3px;
                margin-bottom: 4px;
                color: #495057;
            }
            div.schematic-canvas {
                flex: 1;
                min-height: 100px;
                background-color: #fff;
                border: 2px dashed #dee2e6;
                border-radius: 4px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            div.schematic-canvas-text {
                color: #adb5bd;
                text-align: center;
                font-size: 13px;
                line-height: 1.6;
            }
            div.schematic-table-half {
                flex: 1;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                overflow: hidden;
            }
            span.schematic-status {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
                background-color: #f0f0f0;
            }
            span.schematic-status-disconnected { color: #95a5a6; }
            span.schematic-status-connecting { color: #f39c12; }
            span.schematic-status-authenticated { color: #27ae60; }
            span.schematic-status-failed { color: #e74c3c; }
        """

        return f"<html><head><style>{base_style}</style></head><body>{section['content']}</body></html>"
