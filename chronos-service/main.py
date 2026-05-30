from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
import torch
from chronos import BaseChronosPipeline

pipeline = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    pipeline = BaseChronosPipeline.from_pretrained(
        "amazon/chronos-bolt-base",
        device_map="cpu",
        torch_dtype=torch.float32,
    )
    yield

app = FastAPI(lifespan=lifespan)

class ForecastRequest(BaseModel):
    series: list[int]
    horizon: int = 90

class ForecastResponse(BaseModel):
    curve: list[float]
    peak_day: int
    confidence: float

@app.post("/forecast", response_model=ForecastResponse)
def forecast(req: ForecastRequest):
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Model loading")
    if len(req.series) < 3:
        raise HTTPException(status_code=422, detail="Need at least 3 data points")

    confidence = min(1.0, len(req.series) / 30.0)

    context = torch.tensor(req.series, dtype=torch.float32).unsqueeze(0)
    # predict_quantiles retorna (quantiles, mean)
    # quantiles shape: [batch=1, prediction_length, num_quantiles=1]
    quantiles, _ = pipeline.predict_quantiles(
        context,
        prediction_length=req.horizon,
        quantile_levels=[0.5],
    )
    median = quantiles[0, :, 0].numpy().tolist()
    peak_day = int(np.argmax(median))

    return ForecastResponse(curve=median, peak_day=peak_day, confidence=round(confidence, 2))

@app.get("/health")
def health():
    return {"status": "ok" if pipeline is not None else "loading"}
