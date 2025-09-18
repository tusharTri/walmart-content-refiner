import os
import tempfile
from typing import Tuple, Dict
import pandas as pd
import matplotlib.pyplot as plt


def generate_report(df: pd.DataFrame) -> Tuple[Dict[str, int], str]:
    # Expect a 'violations' column with semicolon-joined strings
    counts: Dict[str, int] = {}
    series = df.get("violations")
    if series is not None:
        for v in series.fillna(""):
            parts = [p.strip() for p in str(v).split(";") if p.strip()]
            for p in parts:
                counts[p] = counts.get(p, 0) + 1

    # Create bar chart of top 10
    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
    labels = [k for k, _ in top]
    values = [v for _, v in top]
    plt.figure(figsize=(10, 4))
    plt.bar(labels, values)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    work_dir = tempfile.mkdtemp(prefix="report-")
    chart_path = os.path.join(work_dir, "violations_chart.png")
    plt.savefig(chart_path)
    plt.close()
    return counts, chart_path


