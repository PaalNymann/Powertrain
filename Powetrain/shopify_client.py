import os
import time
import logging
from typing import List, Dict, Optional, Iterable, Any
import requests
from requests import Session
from dotenv import load_dotenv

load_dotenv()

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

DEFAULT_VERSION = "2024-01"

class ShopifyError(Exception):
    pass

def _required_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing required env var: {name}")
    return val

def _parse_next_page_info(link_header: str) -> Optional[str]:
    if not link_header:
        return None
    for part in link_header.split(","):
        part = part.strip()
        if 'rel="next"' in part:
            # format: <url?page_info=XYZ&limit=...>; rel="next"
            lt = part.find("<")
            gt = part.find(">")
            if lt != -1 and gt != -1:
                url = part[lt + 1:gt]
                for qp in url.split("?")[-1].split("&"):
                    if qp.startswith("page_info="):
                        return qp.split("=", 1)[1]
    return None

class ShopifyClient:
    def __init__(
        self,
        domain: Optional[str] = None,
        token: Optional[str] = None,
        version: Optional[str] = None,
        session: Optional[Session] = None,
        timeout: int = 30,
    ):
        self.domain = domain or _required_env("SHOPIFY_DOMAIN")
        self.token = token or _required_env("SHOPIFY_TOKEN")
        self.version = version or os.getenv("SHOPIFY_VERSION", DEFAULT_VERSION)
        self.timeout = timeout
        self.session = session or requests.Session()
        self.base_admin = f"https://{self.domain}/admin/api/{self.version}"
        self.common_headers = {
            "X-Shopify-Access-Token": self.token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # ------------- Internal request helper with retry (429, 5xx) -------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        max_retries: int = 5,
        backoff_factor: float = 0.8,
    ) -> requests.Response:
        url = f"{self.base_admin}{path}"
        for attempt in range(1, max_retries + 1):
            try:
                r = self.session.request(
                    method,
                    url,
                    headers=self.common_headers,
                    params=params,
                    json=json,
                    timeout=self.timeout,
                )
            except requests.RequestException as e:
                if attempt == max_retries:
                    raise ShopifyError(f"Request failure {method} {path}: {e}") from e
                sleep = backoff_factor * attempt
                LOG.warning("Transient network error (attempt %s/%s) sleeping %.2fs: %s", attempt, max_retries, sleep, e)
                time.sleep(sleep)
                continue

            if r.status_code in (429,) or 500 <= r.status_code < 600:
                if attempt == max_retries:
                    raise ShopifyError(f"HTTP {r.status_code} after {attempt} attempts: {r.text[:300]}")
                retry_after = r.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    sleep = float(retry_after)
                else:
                    sleep = backoff_factor * attempt
                LOG.warning("Retryable status %s (attempt %s/%s). Sleeping %.2fs", r.status_code, attempt, max_retries, sleep)
                time.sleep(sleep)
                continue

            return r
        raise ShopifyError("Unreachable retry loop")

    # ------------- Product helpers -------------
    def iter_products(
        self,
        limit_per_page: int = 250,
        fields: Optional[str] = None,
        max_pages: int = 10_000,
        sleep_seconds: float = 0.05,
    ) -> Iterable[Dict]:
        params = {"limit": limit_per_page}
        if fields:
            params["fields"] = fields
        page_info: Optional[str] = None
        page = 0
        while True:
            page += 1
            if page > max_pages:
                LOG.warning("Stopping after max_pages=%s", max_pages)
                break
            if page_info:
                params["page_info"] = page_info
            else:
                params.pop("page_info", None)

            r = self._request("GET", "/products.json", params=params)
            if r.status_code != 200:
                raise ShopifyError(f"Failed listing products {r.status_code}: {r.text[:400]}")
            data = r.json()
            products = data.get("products", [])
            LOG.debug("Page %s fetched %s products", page, len(products))
            for p in products:
                yield p
            next_pi = _parse_next_page_info(r.headers.get("Link", "") or r.headers.get("link", ""))
            if not next_pi:
                break
            page_info = next_pi
            if sleep_seconds:
                time.sleep(sleep_seconds)

    def fetch_all_products(
        self,
        limit_per_page: int = 250,
        fields: Optional[str] = None,
    ) -> List[Dict]:
        return list(self.iter_products(limit_per_page=limit_per_page, fields=fields))

    def fetch_all_product_ids(self) -> List[int]:
        return [p["id"] for p in self.iter_products(fields="id")]

    def delete_product(self, product_id: int) -> bool:
        r = self._request("DELETE", f"/products/{product_id}.json", max_retries=3)
        if r.status_code == 200:
            return True
        LOG.error("Delete failed %s: %s %s", product_id, r.status_code, r.text[:200])
        return False

    def count_products(self) -> int:
        r = self._request("GET", "/products/count.json", max_retries=3)
        if r.status_code != 200:
            LOG.error("Count error %s: %s", r.status_code, r.text[:200])
            return -1
        return r.json().get("count", -1)

# ------------- Module-level convenience (backwards compat) -------------
_client_singleton: Optional[ShopifyClient] = None

def _client() -> ShopifyClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = ShopifyClient()
    return _client_singleton

def fetch_all_products(limit_per_page: int = 250,
                       max_pages: int = 200,
                       sleep_seconds: float = 0.1,
                       fields: Optional[str] = None) -> List[Dict]:
    # max_pages kept for backward compatibility (ignored internally, we slice)
    products = []
    for i, p in enumerate(_client().iter_products(limit_per_page=limit_per_page, fields=fields, sleep_seconds=sleep_seconds), start=1):
        products.append(p)
        if i // limit_per_page >= max_pages:
            break
    return products

def fetch_all_product_ids() -> List[int]:
    return _client().fetch_all_product_ids()

def delete_product(product_id: int) -> bool:
    return _client().delete_product(product_id)

def count_products() -> int:
    return _client().count_products()

if __name__ == "__main__":
    c = _client()
    print("Count:", c.count_products())
    ids = c.fetch_all_product_ids()
    print("Fetched IDs:", len(ids))