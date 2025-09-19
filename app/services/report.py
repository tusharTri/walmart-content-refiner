import os
import tempfile
from typing import Tuple, Dict
import pandas as pd
# import matplotlib.pyplot as plt  # Disabled due to installation issues


def generate_report(df: pd.DataFrame) -> Tuple[Dict[str, int], str]:
    # Expect a 'violations' column with semicolon-joined strings
    counts: Dict[str, int] = {}
    series = df.get("violations")
    if series is not None:
        for v in series.fillna(""):
            parts = [p.strip() for p in str(v).split(";") if p.strip()]
            for p in parts:
                counts[p] = counts.get(p, 0) + 1

    # Chart generation disabled due to matplotlib installation issues
    chart_path = "chart_disabled_due_to_matplotlib_issues"
    return counts, chart_path



