import httpx
from worker.config import CHRONOS_SERVICE_URL

def get_forecast(series: list[int], horizon: int = 90) -> dict | None:
    try:
        resp = httpx.post(
            f"{CHRONOS_SERVICE_URL}/forecast",
            json={"series": series, "horizon": horizon},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None  # Chronos unavailable: prediction saved as pending
