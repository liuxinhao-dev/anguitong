# 安规通 · 化工安全规程问答助手

> 把几百页的化工安全规程，变成一个能问答、**每个回答都指到具体条款**、**查不到就明说查不到**的助手。

## 为什么做这个

化工安全规程动辄几百页，一线人员遇到具体问题（动火分几级、谁来批、进罐前测什么）不会去翻目录。
直接上通用大模型更危险：它会编，而安全领域编错会出人命。

所以这个项目的重点不是"能回答"，而是三件事：

1. **答得出** —— 按「章/节/条」切片，保证召回的是完整条款，不是被切断的半句话
2. **指得到** —— 每条回答强制给出条款号，能回查原文
3. **不敢答就说不知道** —— 检索置信度低、或模型引用了不在召回结果里的条款，一律拒答

## 效果（填入你的实测数据）

| 指标 | 数值 | 怎么测的 |
|---|---|---|
| 检索命中率 Recall@5 | 【92%】 | 50 条评测集，标准条款是否进前 5 |
| 回答可用率 | 【85%】 | 人工判定 50 条：正确 / 部分正确 / 错误 |
| 拒答正确率 | 【87%】 | 15 条文档外问题，是否正确拒答 |

对比实验：仅向量检索 Recall@5 = 【78%】，加 BM25 混合后 = 【92%】。

## 架构

```
PDF ──► PyMuPDF 解析 ──► 去页眉页脚 ──► 按条款切片（注入章节路径）
                                              │
                        ┌─────────────────────┴─────────────────────┐
                        ▼                                           ▼
                  Chroma 向量检索                              BM25 关键词检索
                        └─────────────────► RRF 融合 ◄──────────────┘
                                              │
                                    DeepSeek 生成（强制 JSON + 引用条款号）
                                              │
                              引用校验失败 / 置信度不足 ──► 拒答
                                              │
                                        Streamlit 界面
```

## 快速开始

### Windows 环境（先看这段，能省你两小时）

**1. 不要用默认的 `python`。** 如果 `python --version` 显示 3.5 或 3.9，说明 PATH 指向了旧版本，
本项目需要 **3.10+**（推荐 3.12）。所有命令都用启动器显式指定：

```powershell
py -3.12 --version          # 确认是 3.12
```

**2. 建虚拟环境**（不要装进系统 Python）：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

**3. 装依赖走国内镜像**（依赖树含 onnxruntime，约 1–2 GB，直连常超时）：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt `
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120
```

**4. 不需要 `activate`。** 直接调 `.venv\Scripts\python.exe` 更稳，
可以绕开 PowerShell 的「禁止运行脚本」策略：

```powershell
.\.venv\Scripts\python.exe check_env.py     # 自检：告诉你还缺什么
```

也可以一条命令装完：`powershell -ExecutionPolicy Bypass -File setup.ps1`

### 然后

```powershell
copy .env.example .env      # 填 DEEPSEEK_API_KEY 和 EMBED_API_KEY

# 把规程 PDF 放进 data/（仓库不含 PDF，自行准备）
.\.venv\Scripts\python.exe check_env.py      # 确认全绿
.\.venv\Scripts\python.exe ingest.py         # 构建索引
.\.venv\Scripts\python.exe answer.py "动火作业分几级"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### 放哪

项目目录用**纯英文路径**，别放在中文目录下（个别库对非 ASCII 路径不友好）。
C 盘空间紧张就放 `D:\projects\anguitong`。

## 目录

| 文件 | 作用 |
|---|---|
| `config.py` | 参数与密钥读取（全部走环境变量） |
| `ingest.py` | PDF 解析、清洗、结构化切片、建索引 |
| `retrieve.py` | 向量 + BM25 混合召回，RRF 融合 |
| `answer.py` | 带引用约束的生成 + 双重拒答 |
| `app.py` | Streamlit 对话界面 |
| `eval/run_eval.py` | 跑评测集，输出指标与明细 |

## 已知限制

- 扫描版 PDF（图片型）解析不出来，需要先 OCR
- 表格跨页时结构会丢，目前只保留文字
- 评测集 50 条由本人标注，样本小，不覆盖长尾问法
- 单文档场景，多文档需要对条款号做来源区分

## 免责声明

学习用途的项目演示，输出**不能替代正式的安全审查与作业许可流程**。实际作业请以企业现行规程和安全管理人员意见为准。
