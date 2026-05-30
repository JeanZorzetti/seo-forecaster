from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
import torch
from chronos import ChronosPipeline

app = FastAPI()

pipeline = ChronosPipeline.from_pretrained(
    "amazon/chronos-bolt-base",
    device_map="cpu",
    torch_dtype=torch.float32,
)

class ForecastRequest(BaseModel):
    series: list[int]
    horizon: int = 90

class ForecastResponse(BaseModel):
    curve: list[float]
    peak_day: int
    confidence: float

@app.post("/forecast", response_model=ForecastResponse)
def forecast(req: ForecastRequest):
    if len(req.series) < 3:
        raise HTTPException(status_code=422, detail="Need at least 3 data points")

    confidence = min(1.0, len(req.series) / 30.0)

    context = torch.tensor(req.series, dtype=torch.float32).unsqueeze(0)
    forecast_tensor = pipeline.predict(context, prediction_length=req.horizon)
    median = forecast_tensor[0, 1, :].numpy().tolist()
    peak_day = int(np.argmax(median))

    return ForecastResponse(curve=median, peak_day=peak_day, confidence=round(confidence, 2))

@app.get("/health")
def health():
    return {"status": "ok"}
