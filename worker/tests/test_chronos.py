from unittest.mock import patch, MagicMock
from worker.forecast.chronos import get_forecast

def test_get_forecast_success():
    mock_response = {
        "curve": [10.0] * 90,
        "peak_day": 30,
        "confidence": 0.8,
    }
    with patch("worker.forecast.chronos.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp
        result = get_forecast([5, 10, 20, 40], horizon=90)
    assert result["peak_day"] == 30
    assert result["confidence"] == 0.8
    assert len(result["curve"]) == 90

def test_get_forecast_returns_none_on_error():
    with patch("worker.forecast.chronos.httpx.post") as mock_post:
        mock_post.side_effect = Exception("Chronos unavailable")
        result = get_forecast([5, 10, 20], horizon=90)
    assert result is None

def test_get_forecast_returns_none_on_http_error():
    with patch("worker.forecast.chronos.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("422 Unprocessable")
        mock_post.return_value = mock_resp
        result = get_forecast([5, 10, 20], horizon=90)
    assert result is None
