from __future__ import annotations
from urllib.parse import urlparse

async def parse_sec_url(url: str) -> tuple[str, str]:
    """
    從 SEC filing URL 解析出 cik 和 accession number。
    範例 URL：https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm
    """
    parsed = urlparse(url)
    path = parsed.path
    parts = path.strip("/").split("/")
    if len(parts) < 5:
        raise ValueError("URL 格式不正確，無法解析 cik 和 accession number")
    
    cik_raw = parts[3]
    acc_clean = parts[4]

    cik = cik_raw.zfill(10)
    accession = (
        f"{acc_clean[:10]}-"
        f"{acc_clean[10:12]}-"
        f"{acc_clean[12:]}"
    )
    return cik, accession