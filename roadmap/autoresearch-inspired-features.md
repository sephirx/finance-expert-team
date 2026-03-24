# AutoResearch 启发的功能规划

> 参考项目：https://github.com/sephirx/autoresearch
> 核心模式：markdown 驱动指令 → agent 自动改参数/代码 → 固定时间跑实验 → 评估指标 → 循环迭代

---

## Feature 1：Watchlist 批量分析

**优先级**：高（最容易落地）
**状态**：待开发

### 目标
当前系统是单 ticker 交互式，每次手动跑 `main.py`。
借鉴 AutoResearch 的 overnight 批量跑思路，支持一次性分析多只股票并生成对比报告。

### 设计思路
- 读取 `memory/portfolio.json` 中的 watchlist
- 对每只股票依次运行指定 agents
- 汇总输出对比报告（谁最值得关注）
- 支持定时触发（如每日收盘后自动跑）

### 入口示例
```bash
python main.py --batch watchlist --agents fundamental risk
python main.py --batch "AAPL,NVDA,TSLA" --query "谁的估值最低"
```

### 输出
- Markdown 对比表格
- HTML 多股票 dashboard（Plotly）

---

## Feature 2：research.md 结构化研究指令系统

**优先级**：中
**状态**：待开发

### 目标
把 `--query` 自然语言升级为结构化的 `research.md` 文件，支持更复杂的多步研究任务。
类比 AutoResearch 的 `program.md` 驱动 agent 行为的思路。

### 设计思路
- 用户编写 `research.md` 定义研究目标、约束、评判标准
- `main.py` 检测到 `--research` 参数时读取该文件
- intent_router 解析结构化指令，分发给对应 agents

### research.md 格式示例
```markdown
## 研究目标
对比 NVDA vs AMD 的估值洼地

## 股票列表
NVDA, AMD

## 使用 Agents
fundamental, risk

## 时间范围
最近 2 个季度

## 评判标准
PEG ratio < 1 且 ROE > 20%
```

### 入口示例
```bash
python main.py --research research.md
```

---

## Feature 3：策略参数自动调优

**优先级**：中高
**状态**：待开发

### 目标
让 agent 自动迭代 `core/config.py` 中的 signal weights，找到使回测指标最优的参数组合。
类比 AutoResearch 修改 `train.py` + 固定时间跑实验的核心循环。

### 设计思路
- 固定回测数据窗口（如 1 年历史数据）
- 每次迭代修改 config 中的权重组合
- 用单一指标评判（Sharpe ratio / max drawdown）
- 记录每次实验结果，保留最优配置
- overnight 可跑 50~100 次迭代

### 核心循环
```
读 config → 修改权重 → 回测 → 计算 Sharpe → 记录 → 下一轮
```

### 依赖
- 需先完善 `strategies/` 下的回测引擎
- 需定义统一的评估指标接口

---

## Feature 4：Agent 提示词自动优化

**优先级**：低（长期）
**状态**：概念阶段

### 目标
类比 AutoResearch 中 agent 修改 `train.py` 的思路：
让 meta-agent 自动优化各分析 agent 内部的提示词，用 scorecard 评分作为优化指标。

### 设计思路
- 固定 `base_agent.py`（不动，类比 `prepare.py`）
- meta-agent 修改各 agent 的分析 prompt 模板
- 用 `scorecard_agent.py` 的综合评分作为 `val_bpb` 等效指标
- 对同一只股票用不同 prompt 版本跑，选评分最高的保留

### 挑战
- 评分指标需要与真实投资结果挂钩才有意义
- prompt 搜索空间大，需要引导性变异策略

---

## 优先级总结

| # | 功能 | 实现难度 | 业务价值 | 当前状态 |
|---|------|---------|---------|---------|
| 1 | Watchlist 批量分析 | 低 | 立即可用 | 待开发 |
| 2 | research.md 指令系统 | 中 | 提升交互质量 | 待开发 |
| 3 | 策略参数自动调优 | 高 | 核心竞争力 | 待开发 |
| 4 | Agent 提示词自动优化 | 高 | 长期收益 | 概念阶段 |
