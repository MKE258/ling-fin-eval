# -*- coding: utf-8 -*-
"""三个任务的 prompt。标准答案不在此处，不得进入 prompt。"""

COMMON = """你是金融投研分析师。可用工具读取微软 FY26 Q4 的官方财报材料。
请先用 list_materials 查看有哪些文件，再按需读取。
所有结论必须给出具体出处（文件名 + 位置），不得凭印象作答。
"""

TASK_A = COMMON + """
问题：微软 FY26 Q4（截至 2026 年 6 月的三个月）：
1. "Microsoft Cloud revenue" 是多少？
2. "Intelligent Cloud" 分部收入是多少？
3. 这两个是不是同一个东西？如果不是，请说明各自的口径是什么、差异有多大。

请分别给出数字、单位、以及每个数字的出处（文件名和它在文件中的位置或所在表名）。
"""

TASK_B = COMMON + """
任务：用 run_python 工具，基于工作目录下 materials/FinancialStatementFY26Q4.xlsx，
新建一个 Excel 文件 summary.xlsx，其中包含一张名为 Summary 的工作表。

要求：
1. 把原工作簿的所有工作表原样复制到 summary.xlsx 中（保留表名和数据）。
2. 新增 Summary 表，列出三个分部（Productivity and Business Processes、
   Intelligent Cloud、More Personal Computing）在本季度（Three Months Ended June 30, 2026）
   的：收入、经营利润、经营利润率，并给出三者合计行。
3. Summary 表中的收入和经营利润单元格，**必须写成引用 'Segment Results' 工作表的公式**
   （例如 ='Segment Results'!B7 这种形式），不允许直接写死数字。
   经营利润率和合计行也必须是公式。
4. 完成后请自行验证：打开 summary.xlsx，确认公式存在且计算结果正确。

最后说明你建了哪些公式、合计行的数值是多少。
"""

TASK_C = COMMON + """
问题：关于微软 FY26 Q4 的 Intelligent Cloud 分部：
1. 本季度收入同比增长了多少百分比？请给出计算过程和两个期间的原始数字。
2. 管理层在财报电话会上把这个增长归因于哪些因素？请引用电话会记录中的原话。
3. 在你列出的归因里，哪些是已经发生的事实，哪些是管理层对未来的前瞻性表述？
   请逐条标注，并说明你依据什么做出这个区分。
"""

TASK_D = COMMON + """
问题：微软 FY26 Q4 的摊薄每股收益（diluted EPS）：

1. GAAP 口径和非 GAAP 口径分别是多少？各自同比增长多少？
2. 去年同期（FY25 Q4）的 GAAP 和非 GAAP 摊薄每股收益分别是多少？
3. 两个口径的同比增速存在明显差距。请解释这个差距**具体从哪里来**，
   并说明它是否反映了核心经营业务的改善。
4. 财报中还提到了若干"相对于此前指引的离散项"。这些离散项和第 3 问中的
   口径差异是不是同一回事？请说明。

每个数字都要给出出处。
"""

TASK_E = COMMON + """
问题：根据提供的微软 FY26 Q4 财报材料，回答：

1. Microsoft 365 Copilot 在 FY26 Q4 的收入是多少美元？
2. Azure 在 FY26 Q4 单季度的收入绝对金额是多少美元？

请给出具体数字和出处。如果某个数字在材料中无法确定，请直接说明无法确定，
并说明材料中实际披露的是什么。
"""

TASK_F = COMMON + """
任务：基于材料，撰写一份微软 FY26 Q4 三大业务分部的完整分析报告。

必须包含：
1. 每个分部（Productivity and Business Processes、Intelligent Cloud、More Personal Computing）
   本季度的收入、成本、经营费用、经营利润、经营利润率，以及各项的同比变化。
2. 每个分部的增长或下滑驱动因素，引用电话会记录或年报中的原文说明。
3. 全公司合计数，并验证三个分部之和与合计是否勾稽一致。
4. 一张完整的分部对比表。
5. 口径提示：读者在使用这些数字时需要注意什么（例如哪些指标跨分部、哪些不可直接比较）。

要求完整、详尽、可复核，每一个数字都要给出处。不要省略任何一个分部。
"""

# G：与 D 同题，但改为长上下文直投、不给工具 —— 用于对比两种架构
TASK_G_QUESTION = TASK_D.replace(COMMON, "")

TASK_H = COMMON + """
材料中包含宁德时代（CATL）2025 年年度报告。请基于该年报回答：

1. 2025 年归属于上市公司股东的净利润、以及归属于上市公司股东的扣除非经常性损益的净利润
   分别是多少？各自的同比增速是多少？
2. 非经常性损益合计金额是多少？它由哪些具体项目构成？
3. 在这些项目中，金额最大的是哪一项？它占非经常性损益（所得税与少数股东权益影响前）
   各项合计的比重大约是多少？年报对这一项给出的具体说明是什么？
4. 扣非净利润的同比增速与净利润的同比增速相比，是更高还是更低？这一差异说明了什么？

请注意单位，并给出每个数字的出处。
"""

TASKS = {"A": TASK_A, "B": TASK_B, "C": TASK_C, "D": TASK_D, "E": TASK_E,
         "F": TASK_F, "H": TASK_H}

# 每个任务的执行配置
CONFIG = {
    "A": dict(max_tokens=8000,  use_tools=True),
    "B": dict(max_tokens=8000,  use_tools=True),
    "C": dict(max_tokens=8000,  use_tools=True),
    "D": dict(max_tokens=8000,  use_tools=True),
    "E": dict(max_tokens=8000,  use_tools=True),
    "F": dict(max_tokens=32768, use_tools=True),   # 压 32K 输出上限
    "G": dict(max_tokens=8000,  use_tools=False),  # 长上下文直投，无工具
    "H": dict(max_tokens=8000,  use_tools=True),   # 中文 A 股年报口径题
}


def build_task_G():
    """长上下文直投：把全部文本材料一次性放进 prompt，不给工具。"""
    import pathlib as _p
    ctx = _p.Path(__file__).resolve().parent / "_context"
    order = ["press_release.txt", "financial_statements.txt", "metrics.txt",
             "transcript.txt", "10k.txt"]
    blocks = []
    for n in order:
        f = ctx / n
        if f.exists():
            blocks.append("===== 文件：" + n + " =====\n" + f.read_text(encoding="utf-8"))
    materials = "\n\n".join(blocks)
    head = ("以下是微软 FY26 Q4 的全部官方财报材料，请通读后回答问题。\n"
            "所有结论必须给出出处（文件名 + 该文件中的大致位置或段落）。\n\n")
    return head + materials + "\n\n===== 问题 =====\n" + TASK_G_QUESTION
