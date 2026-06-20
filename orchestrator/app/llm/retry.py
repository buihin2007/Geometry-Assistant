import asyncio
import httpx

# Free tier hay 429 do giới hạn theo PHÚT (RPM). Retry ngắn với backoff để
# vượt qua spike tạm thời mà không làm hỏng request (PLAN §4.1 lưu ý vận hành).


async def post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_retries: int = 4,
    base_delay: float = 8.0,
    max_delay: float = 30.0,
    **kwargs,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        resp = await client.post(url, **kwargs)
        if resp.status_code != 429:
            return resp
        # 429: tôn trọng Retry-After nếu có, ngược lại backoff lũy thừa.
        if attempt == max_retries:
            return resp  # để caller raise_for_status báo lỗi rõ ràng
        retry_after = resp.headers.get("retry-after")
        try:
            delay = float(retry_after) if retry_after else base_delay * (2**attempt)
        except ValueError:
            delay = base_delay * (2**attempt)
        await asyncio.sleep(min(delay, max_delay))
    # không tới được, nhưng để an toàn:
    if last_exc:
        raise last_exc
    return resp
