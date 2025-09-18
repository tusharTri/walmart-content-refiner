from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from typing import Optional
import pandas as pd
import tempfile
import os
from app.models import ProductInput, ProductOutput
from app.services.refiner_service import refine_product
from app.services.data_loader import load_csv, save_csv
from app.config import get_settings, get_logger, Settings

router = APIRouter()


@router.get("/")
def root():
    return {"message": "Walmart Content Refiner API"}


@router.post("/refine", response_model=ProductOutput, status_code=200)
def refine(item: ProductInput, settings: Settings = Depends(get_settings)) -> ProductOutput:
    try:
        return refine_product(item)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refine-batch")
async def refine_batch(
    csv_url: Optional[str] = None,
    file: Optional[UploadFile] = File(default=None),
    settings: Settings = Depends(get_settings),
):
    logger = get_logger()
    try:
        if not csv_url and not file:
            raise HTTPException(status_code=400, detail="Provide csv_url or file upload")

        work_dir = tempfile.mkdtemp(prefix="refine-")
        input_path = os.path.join(work_dir, "input.csv")
        output_path = os.path.join(work_dir, "output.csv")

        if file:
            content = await file.read()
            with open(input_path, "wb") as f:
                f.write(content)
        else:
            # Treat csv_url as local path or accessible path
            if not os.path.exists(csv_url):
                raise HTTPException(status_code=400, detail="csv_url not found on local filesystem")
            input_path = csv_url

        df = load_csv(input_path)
        outputs = []
        for _, row in df.iterrows():
            inp = ProductInput(
                brand=row.get("brand", ""),
                product_type=row.get("product_type", ""),
                attributes=row.get("attributes", {}),
                current_description=row.get("current_description", ""),
                current_bullets=row.get("current_bullets", []),
            )
            out = refine_product(inp)
            outputs.append({
                "refined_title": out.title,
                "refined_bullets": "|".join(out.bullets),
                "refined_description": out.description,
                "meta_title": out.meta_title,
                "meta_description": out.meta_description,
                "violations": "; ".join(out.violations),
            })

        out_df = pd.concat([df.reset_index(drop=True), pd.DataFrame(outputs)], axis=1)
        save_csv(out_df, output_path)

        job_id = os.path.basename(work_dir)
        return JSONResponse(status_code=200, content={"job_id": job_id, "result_path": output_path})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Batch refine failed")
        raise HTTPException(status_code=500, detail=str(e))
