# 电商数据爬虫 + 可视化看板

一个完整的电商数据采集、存储与分析系统，支持多平台商品数据采集和交互式可视化看板。

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.38%2B-red)

## 📋 项目简介

本项目是一个功能完善的电商数据采集与分析系统，主要特性包括：

- **多平台爬虫**: 支持京东(JD)、天猫(Tmall)等平台的数据采集
- **官方 API 优先**: 配置京东联盟 API 或淘宝开放平台 API 后，优先走真实接口
- **兼容降级**: 没有 API 账号时自动回退到 HTML 解析，再回退到模拟数据
- **异步并发**: 使用 aiohttp 实现高效异步请求
- **智能调度**: APScheduler 定时任务自动采集
- **数据存储**: SQLAlchemy ORM + SQLite/MySQL 双支持
- **可视化看板**: Streamlit 交互式数据展示
- **RESTful API**: FastAPI 提供完整的数据查询接口
- **数据导出**: 支持 CSV/JSON 格式导出

## 🛠️ 技术栈

| 类别 | 技术 |
|------|------|
| 爬虫框架 | aiohttp, BeautifulSoup4, lxml |
| 数据存储 | SQLAlchemy, SQLite/MySQL |
| 可视化 | Streamlit, Plotly |
| API框架 | FastAPI, Uvicorn |
| 定时任务 | APScheduler |
| 数据处理 | Pandas, NumPy |
| 日志 | Loguru |

## 📦 安装步骤

### 1. 进入项目目录

```powershell
cd E:\项目测试\ecommerce-data-crawler
```

### 2. 安装依赖

```powershell
pip install -r requirements.txt
```

### 3. 创建数据目录

```powershell
mkdir data logs
```

## ☁️ Streamlit Community Cloud 部署

这个项目已经补好了可直接部署的入口：
- 根目录 `app.py` 作为 Streamlit 入口
- `.streamlit/config.toml` 提供云端默认配置
- `dashboard/app.py` 已修复看板的异步调用问题

### 部署步骤
1. 把代码推到 GitHub 仓库。
2. 登录 Streamlit Community Cloud，选择这个仓库。
3. Main file path 填 `app.py`。
4. 如需真实数据，配置 `config.ini` 对应的 API 参数，或者通过仓库环境变量注入。
5. 点击 Deploy，生成一个可以直接分享的公网链接。

### 云端注意事项
- Streamlit Cloud 的免费环境更适合演示和看板展示。
- SQLite 数据文件适合轻量演示；若你要长期在线更新，建议后续换成云数据库。
- 如果没有真实 API 配置，页面仍可打开，但数据依赖本地/已采集内容。

## 🚀 快速开始

### 模式1: 运行演示（推荐新手）

```powershell
python main.py --mode demo
```

项目会先尝试使用官方 API；如果没有配置，则自动回退到 HTML 解析或模拟数据。

### 模式2: 单次爬取

```powershell
# 爬取京东手机数码
python main.py --mode crawl-once --platform jd --category 手机数码 --count 50

# 爬取天猫笔记本电脑
python main.py --mode crawl-once --platform tmall --category 笔记本电脑 --count 30
```

### 模式3: 启动可视化看板

```powershell
python main.py --mode dashboard
```

看板将在 http://localhost:8501 启动。

### 模式4: 启动API服务

```powershell
python main.py --mode api
```

API 文档将在 http://localhost:8000/docs 启动。

## 🔌 官方 API 配置

如果你已经拿到京东联盟 API 或淘宝开放平台 API，编辑 `config.ini`：

```ini
[jd_api]
enabled = true
base_url = https://api.jd.com/routerjson
app_key = your_app_key
app_secret = your_app_secret
access_token = your_access_token
method = jd.union.open.goods.jsearch
response_path = jd_union_open_goods_jsearch_res.data
extra_params = adzone_id=你的推广位ID

[tmall_api]
enabled = true
base_url = https://eco.taobao.com/router/rest
app_key = your_app_key
app_secret = your_app_secret
access_token = your_access_token
method = taobao.tbk.dg.material.optional
response_path = tbk_dg_material_optional_response.result_list.map_data
extra_params = adzone_id=你的推广位ID
```

当前实现是官方 API 适配器：
- 京东、淘宝分别走各自的签名和参数组装
- 通过 `method`、`response_path`、`extra_params` 适配不同接口
- 如果你拿到的官方接口返回结构不同，只需要改配置，不必改代码

## 📖 使用说明

### 项目结构

```
ecommerce-data-crawler/
├── main.py                  # 主程序入口
├── app.py                   # Streamlit Cloud 入口
├── config.ini               # 配置文件
├── requirements.txt         # Python依赖
├── README.md                # 项目文档
├── crawler/                 # 爬虫模块
├── models/                  # 数据模型
├── storage/                 # 数据存储
├── dashboard/               # 可视化看板
├── api/                     # API服务
├── utils/                   # 工具模块
├── data/                    # 数据目录
├── logs/                    # 日志目录
└── tests/                   # 测试目录
```

### 配置说明

编辑 `config.ini` 修改采集类目、平台和 API 参数。

## 🧪 运行测试

```powershell
pytest tests/ -v
```

## 📝 注意事项

1. **官方 API 优先**: 有真实接口就用真实接口，没配置时会降级。
2. **合规使用**: 请遵守相关法律法规和平台开放平台协议。
3. **字段差异**: 京东联盟和淘宝开放平台的返回字段通常不一样，真实接入时建议按官方文档补专用映射。
4. **数据库**: 默认使用 SQLite，生产环境建议切换到 MySQL 或 PostgreSQL。

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 License

MIT License

## 👨‍💻 关于作者

本项目使用 Codex AI 辅助开发，旨在帮助初学者学习爬虫、数据处理和可视化的完整流程。

## 📅 更新日志

### v1.0.0 (2026-07-15)
- 初始版本发布
- 支持京东、天猫平台数据采集
- 集成 Streamlit 可视化看板
- 提供 FastAPI REST 接口
- 定时任务调度器
- 增加官方 API 优先模式
