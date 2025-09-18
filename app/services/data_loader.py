import pandas as pd
from typing import List, Dict


def load_csv(path: str) -> List[Dict]:
    df = pd.read_csv(path)
    return df.fillna("").to_dict(orient="records")


def write_csv(path: str, rows: List[Dict]) -> None:
    if not rows:
        pd.DataFrame().to_csv(path, index=False)
        return
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
