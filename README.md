# Minecraft Benchmark 生成与评测

## 1. 环境安装

```bash
pip install gymnasium numpy requests pillow loguru python-dotenv typer fastapi uvicorn pydantic imageio imageio-ffmpeg mt-paas-sandbox-python-sdk==1.0.8
```

```bash
export AGENT_API_KEY="xxx"
export AGENT_API_BASE="https://aigc.sankuai.com/v1/openai/native"
export FRIDAY_SANDBOX_TOKEN="xxx"
export FRIDAY_SANDBOX_ENDPOINT="https://model.sankuai.com/sandboxGateway/system/587"
```

## 2. 生成Benchmark

使用`generate_benchmark.py`生成Minecraft评测任务。其中`benchmark_shuffled`是论文中用于评测的benchmark，包括1跳-4跳的各种评测任务

生成benchmark的方法如下：

```bash
python generate_benchmark.py multi \
    --model aws.claude-opus-4.6 \
    --num-samples 10 \
    --k-min 1 \
    --k-max 1 \
    --candidate-num 1 \
    --output benchmark_new
```

### 主要参数说明

| 参数 | 说明 |
|------|------|
| `multi`/`single` | 多智能体/单智能体生成benchmark，论文中采用多智能体，效果更好，但因为需要和沙盒交互，生成benchmark速度很慢 |
| `--model` | 模型名称 |
| `--num-samples` | 生成样本数量 |
| `--k-min/--k-max` | 每个样本的子任务数量范围，例如如果希望全部都是单跳任务就设置为1 |
| `--candidate-num` | 候选原子任务数量 |
| `--output` | 输出目录 |

### 输出结构

```
benchmark_new/
├── 0000/
│   └── multi-agent/
│       ├── metadata.json        # 场景配置
│       ├── milestones.json      # 里程碑定义
│       ├── reasoning_graph.json # 依赖图
│       └── debate_log.json      # 聊天日志
├── 0001/
│   └── multi-agent/
│       └── ...
```

## 3. 评测Benchmark

使用`eval_benchmark.py`在生成的benchmark上运行智能体并评估表现。

### 评测策略

1. 调用Sankuai API

```bash
python eval_benchmark.py \
    --model aws.claude-opus-4.6 \
    --benchmark-dir benchmark_new \
    --output-dir results \
    --num-workers 10 \
    --resume
```

2. 本地bllm服务

使用前先挂起vllm：
```bash
python -m vllm.entrypoints.openai.api_server \
    --model Qwen2.5-7B \
    --port 8000
```

```bash
python eval_benchmark.py \
    --model Qwen2.5-7B \
    --benchmark-dir benchmark_new \
    --output-dir results \
    --num-workers 10 \
    --use-vllm \
```

### 通用参数说明

| 参数 | 说明 |
|------|------|
| `--model` | 评测使用的模型 |
| `--benchmark-dir` | benchmark目录路径 |
| `--output-dir` | 输出目录 |
| `--num-workers` | 并行开启的沙盒任务数 |
| `--resume` | 断点续传（跳过已完成的） |
| `--limit` | 限制评测样本数量（测试用） |

### 输出结构

```
results/
└── aws.claude-opus-4.6/
    ├── 0000/
    │   ├── result.json       # 评测结果
    │   ├── episode.mp4       # 视频回放
    │   └── messages/         # 对话记录
    ├── 0001/
    │   └── ...
    └── eval_summary.json     # 汇总统计
```
