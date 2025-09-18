import json
import pandas as pd
import streamlit as st
from app.services.data_loader import load_csv, save_csv
from app.models import ProductInput
from app.services.refiner_service import refine_product

st.set_page_config(page_title="Walmart Content Refiner", layout="wide")
st.title("Walmart Content Refiner")

uploaded = st.file_uploader("Upload CSV", type=["csv"]) 
use_sample = st.checkbox("Use sample_input.csv")

if uploaded or use_sample:
    if uploaded:
        df = pd.read_csv(uploaded)
    else:
        df = load_csv("sample_input.csv")

    st.write("Loaded rows:", len(df))

    if st.button("Run refinement"):
        outs = []
        for _, row in df.iterrows():
            inp = ProductInput(
                brand=row.get("brand", ""),
                product_type=row.get("product_type", ""),
                attributes=row.get("attributes", {}),
                current_description=row.get("current_description", ""),
                current_bullets=row.get("current_bullets", []),
            )
            out = refine_product(inp)
            outs.append({
                "refined_title": out.title,
                "refined_bullets": json.dumps(out.bullets, ensure_ascii=False),
                "refined_description": out.description,
                "meta_title": out.meta_title,
                "meta_description": out.meta_description,
                "violations": "; ".join(out.violations),
            })
        out_df = pd.concat([df.reset_index(drop=True), pd.DataFrame(outs)], axis=1)
        st.dataframe(out_df, use_container_width=True)
        st.download_button("Download refined CSV", data=out_df.to_csv(index=False).encode('utf-8'), file_name="refined.csv", mime="text/csv")


