import os
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Iterable
import logging
import math

logger = logging.getLogger(__name__)

class GridStatusAPIService:
    def __init__(self):
        self.api_key = os.getenv("GRIDSTATUS_API_KEY", "")
        self.base_url = os.getenv("GRIDSTATUS_BASE_URL", "https://api.gridstatus.io")
        if not self.api_key:
            logger.warning("GRIDSTATUS_API_KEY is empty; set it in env.")
        self.headers = {"x-api-key": self.api_key, "accept": "application/json"}
        
        # Global spacing (was 1.25s)
        self._min_interval = 1.35  # seconds

        # Token bucket for 30/min ceiling
        self._bucket_capacity = 30
        self._bucket_tokens = self._bucket_capacity
        self._bucket_refill_rate = self._bucket_capacity / 60.0  # tokens per second
        self._bucket_last_refill = None

        # Simple memo cache: {(url, frozenset(params.items())): (timestamp, httpx.Response)}
        self._memo_ttl = 8.0  # seconds
        self._memo: dict = {}


        # Canonical datasets (unchanged)
        self.iso_datasets: Dict[str, Dict[str, str]] = {
            "PJM": {
                "lmp_hourly_da": "pjm_lmp_day_ahead_hourly",
                "lmp_5min_rt": "pjm_lmp_real_time_5_min",
                "default_location": "PJM-RTO ZONE",
                "filter_candidates": ["location_name", "location", "pnode_name", "name"],
            },
            "CAISO": {
                "lmp_hourly_da": "caiso_lmp_day_ahead_hourly",
                "lmp_5min_rt": "caiso_lmp_real_time_5_min",
                "default_location": "TH_NP15_GEN-APND",
                "filter_candidates": ["location_name", "location", "name"],
            },
            "ERCOT": {
                "lmp_hourly_da": "ercot_spp_day_ahead_hourly",
                "lmp_5min_rt": "ercot_spp_real_time_15_min",  # 15-min
                "default_location": "HB_HOUSTON",
                "filter_candidates": ["settlement_point", "location_name", "location", "name"],
            },
            "NYISO": {
                "lmp_hourly_da": "nyiso_lmp_day_ahead_hourly",
                "lmp_5min_rt": "nyiso_lmp_real_time_5_min",
                "default_location": "N.Y.C.",
                "filter_candidates": ["location_name", "location", "name"],
            },
            "MISO": {
                "lmp_hourly_da": "miso_lmp_day_ahead_hourly",
                "lmp_5min_rt": "miso_lmp_real_time_5_min",
                "default_location": "HUB",
                "filter_candidates": ["location_name", "location", "name"],
            },
        }

        # Global, in-process rate limiter (1 req / 1.25s)
        self._last_call_ts: Optional[float] = None
        self._lock = asyncio.Lock()
        self._min_interval = 1.25  # seconds

    # ----------------- helpers -----------------

    def _get_iso_from_node(self, node: str) -> str:
        u = (node or "").upper()
        if u.startswith("PJM"): return "PJM"
        if u.startswith("CAISO") or u.startswith("TH_") or "GEN-APND" in u: return "CAISO"
        if u.startswith("ERCOT") or u.startswith("HB_"): return "ERCOT"
        if u.startswith("NYISO") or "N.Y.C." in u: return "NYISO"
        if u.startswith("MISO"): return "MISO"
        logger.warning(f"Unknown node '{node}', defaulting to PJM")
        return "PJM"

    def _dataset_for_iso(self, iso: str, rt: bool) -> str:
        info = self.iso_datasets.get(iso)
        if not info:
            raise ValueError(f"ISO '{iso}' not supported")
        return info["lmp_5min_rt"] if rt else info["lmp_hourly_da"]

    def _filter_candidates_for_iso(self, iso: str) -> List[str]:
        info = self.iso_datasets.get(iso, {})
        return info.get("filter_candidates", ["location_name", "location", "name"])

    def _normalize_node(self, iso: str, node: str) -> str:
        u = (node or "").upper().replace(" ", "").replace("_", "").replace("-", "")
        if iso == "PJM":
            if u in {"PJMRTO", "PJMRTOZONE"}: return "PJM-RTO ZONE"
        if iso == "CAISO":
            if u in {"NP15", "THNP15GENAPND"}: return "TH_NP15_GEN-APND"
        if iso == "ERCOT":
            if u in {"HBHOUSTON", "HOUSTON"}: return "HB_HOUSTON"
        if iso == "NYISO":
            if u in {"NYC", "NEWYORKCITY", "NYISO-NYC"}: return "N.Y.C."
        return node

    def _node_aliases(self, iso: str, node: str) -> List[str]:
        """Try a few common textual variants for robustness."""
        base = self._normalize_node(iso, node)
        s = base.replace("_", " ").replace("-", " ")
        comp = s.replace(" ", "")
        aliases = {base}
        if iso == "PJM":
            # PJM-RTO ZONE variants
            aliases |= {"PJM-RTO ZONE", "PJM-RTO", "PJM RTO", "PJM RTO ZONE"}
        if iso == "CAISO" and "NP15" in base:
            aliases |= {"TH_NP15_GEN-APND", "TH NP15 GEN APND", "NP15"}
        if iso == "ERCOT" and "HOUSTON" in base:
            aliases |= {"HB_HOUSTON", "HB HOUSTON", "HOUSTON"}
        # Include compact/no-space variant
        aliases.add(comp)
        # Return deterministic order
        return list(dict.fromkeys(a.strip() for a in aliases if a.strip()))

    @staticmethod
    def _pick_timestamp(rec: Dict) -> Optional[str]:
        for k in ("interval_start_utc", "interval_start", "timestamp_utc", "datetime_utc", "datetime"):
            if rec.get(k):
                return rec[k]
        return None

    @staticmethod
    def _pick_price(rec: Dict) -> Optional[float]:
        for k in ("total_lmp", "lmp", "price", "value"):
            v = rec.get(k)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
        return None

    @staticmethod
    def _pick_congestion(rec: Dict) -> float:
        for k in ("congestion_lmp", "congestion"):
            v = rec.get(k)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
        return 0.0

    @staticmethod
    def _pick_loss(rec: Dict) -> float:
        for k in ("loss_lmp", "loss"):
            v = rec.get(k)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
        return 0.0

    async def _rate_limited_get(self, url: str, params: Dict) -> httpx.Response:
        """
        - Global spacing (min interval between *any* requests)
        - Per-minute token bucket (30/min)
        - Honor Retry-After header on 429/5xx if present
        - Small memo cache to dedupe identical calls made seconds apart
        """
        key = (url, frozenset(params.items()))
        now = asyncio.get_event_loop().time()

        # 0) quick memo hit
        if key in self._memo:
            ts, cached = self._memo[key]
            if now - ts <= self._memo_ttl:
                return cached
            else:
                self._memo.pop(key, None)

        max_attempts = 4
        attempt = 1
        while True:
            # 1) global min-interval spacing
            async with self._lock:
                now = asyncio.get_event_loop().time()
                if self._last_call_ts is not None:
                    elapsed = now - self._last_call_ts
                    if elapsed < self._min_interval:
                        await asyncio.sleep(self._min_interval - elapsed)

                # 2) token bucket refill
                if self._bucket_last_refill is None:
                    self._bucket_last_refill = now
                else:
                    dt = now - self._bucket_last_refill
                    refill = dt * self._bucket_refill_rate
                    if refill > 0:
                        self._bucket_tokens = min(self._bucket_capacity, self._bucket_tokens + refill)
                        self._bucket_last_refill = now

                # 3) if empty, wait until a token is available
                if self._bucket_tokens < 1.0:
                    need = 1.0 - self._bucket_tokens
                    sleep_needed = need / self._bucket_refill_rate
                    await asyncio.sleep(sleep_needed)
                    # after sleep, update accounting for next loop
                    now = asyncio.get_event_loop().time()
                    self._bucket_tokens = min(self._bucket_capacity, self._bucket_tokens + sleep_needed * self._bucket_refill_rate)
                    self._bucket_last_refill = now

                # consume one token and stamp last call
                self._bucket_tokens -= 1.0
                self._last_call_ts = now

            # 4) make the request (outside lock)
            async with httpx.AsyncClient() as client:
                r = await client.get(url, headers=self.headers, params=params, timeout=30.0)

            # 5) success → memoize and return
            if r.status_code not in (429, 500, 502, 503, 504):
                # keep tiny memo to avoid immediate repeats
                self._memo[key] = (asyncio.get_event_loop().time(), r)
                return r

            # 6) backoff: prefer Retry-After if present
            retry_after = r.headers.get("Retry-After")
            if retry_after:
                try:
                    wait = max(1.0, float(retry_after))
                except ValueError:
                    wait = 2.0
            else:
                # exponential backoff with jitter
                base = 0.9 * (2 ** (attempt - 1))
                jitter = 0.15 * (attempt)  # small additive jitter
                wait = min(8.0, base + jitter)

            if attempt >= max_attempts:
                return r

            await asyncio.sleep(wait)
            attempt += 1

    # ----------------- health -----------------

    async def test_connection(self) -> bool:
        url = f"{self.base_url}/v1/"
        try:
            r = await self._rate_limited_get(url, params={})
            if r.status_code == 200:
                logger.info("GridStatus API connection successful.")
                return True
            if r.status_code == 401:
                logger.error("GridStatus API key is invalid.")
                return False
            logger.warning(f"GridStatus root returned {r.status_code}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to GridStatus API: {e}")
            return False

    # -------------- core querying --------------

    async def _query_lmp_once(
        self,
        dataset: str,
        filter_col: Optional[str],
        filter_val: Optional[str],
        start_iso: str,
        end_iso: str,
        timezone: str,
        limit: int,
    ) -> httpx.Response:
        url = f"{self.base_url}/v1/datasets/{dataset}/query"
        params = {
            "start_time": start_iso,
            "end_time": end_iso,
            "timezone": timezone,
            "limit": limit,
        }
        if filter_col and filter_val:
            params["filter_column"] = filter_col
            params["filter_value"] = filter_val
        return await self._rate_limited_get(url, params)

    async def _query_lmp_adaptive(
        self,
        dataset: str,
        iso: str,
        node_value: str,
        start_iso: str,
        end_iso: str,
        timezone: str = "market",
        limit: int = 10000,
    ) -> List[Dict]:
        """
        Strategy:
          A) Try (filter_col in candidates) × (node aliases).
             - If 200 and non-empty -> return rows
             - If 200 and empty -> try next combo
             - If 400/422 -> next combo
             - If other error -> surface and stop
          B) Fallback: unfiltered pull, then client-side filter by any of the likely keys
        """
        candidates = self._filter_candidates_for_iso(iso)
        aliases = self._node_aliases(iso, node_value)

        # A) try filter combos
        for col in candidates:
            for alias in aliases:
                r = await self._query_lmp_once(dataset, col, alias, start_iso, end_iso, timezone, limit)
                if r.status_code == 200:
                    rows = r.json().get("data", [])
                    if rows:
                        return rows
                    # 200 but empty — keep trying other combos
                    continue
                if r.status_code in (400, 401, 403, 404, 422):
                    logger.debug(f"{dataset} rejected col={col} alias='{alias}' ({r.status_code}): {r.text[:160]}")
                    continue
                logger.error(f"{dataset} query error {r.status_code}: {r.text[:300]}")
                return []

        # B) unfiltered + client-side filter
        logger.info(f"{dataset}: falling back to client-side filtering.")
        r = await self._query_lmp_once(dataset, None, None, start_iso, end_iso, timezone, limit)
        if r.status_code != 200:
            logger.error(f"{dataset} unfiltered query error {r.status_code}: {r.text[:300]}")
            return []

        rows = r.json().get("data", [])
        keys = ("location_name", "location", "pnode_name", "settlement_point", "name")
        alias_set = {a for a in aliases}
        out = []
        for rec in rows:
            for k in keys:
                v = rec.get(k)
                if v and str(v).strip() in alias_set:
                    out.append(rec)
                    break
        return out

    # ----------------- public API -----------------

    async def fetch_day_ahead_prices(self, node: str, date: datetime) -> List[Dict]:
        iso = self._get_iso_from_node(node)
        dataset = self._dataset_for_iso(iso, rt=False)
        node_value = self._normalize_node(iso, node)

        start_iso = date.strftime("%Y-%m-%dT00:00:00Z")
        end_iso = (date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")

        rows = await self._query_lmp_adaptive(dataset, iso, node_value, start_iso, end_iso,
                                              timezone="market", limit=7000)
        if not rows:
            logger.warning(f"No DA data for {node_value} on {date.date()}")
            return []

        out: List[Dict] = []
        for rec in rows:
            ts = self._pick_timestamp(rec)
            price = self._pick_price(rec)
            if ts is None or price is None:
                continue
            out.append({
                "node": node_value,
                "hour_start": ts,
                "close_price": price,
                "congestion": self._pick_congestion(rec),
                "loss": self._pick_loss(rec),
                "created_at": datetime.utcnow().isoformat(),
            })
        return out

    async def fetch_real_time_prices(self, node: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        iso = self._get_iso_from_node(node)
        dataset = self._dataset_for_iso(iso, rt=True)
        node_value = self._normalize_node(iso, node)

        start_iso = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_iso = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        rows = await self._query_lmp_adaptive(dataset, iso, node_value, start_iso, end_iso,
                                              timezone="market", limit=12000)
        if not rows:
            logger.warning(f"No RT data for {node_value} between {start_iso} and {end_iso}")
            return []

        out: List[Dict] = []
        for rec in rows:
            ts = self._pick_timestamp(rec)
            price = self._pick_price(rec)
            if ts is None or price is None:
                continue
            out.append({
                "node": node_value,
                "timestamp": ts,
                "price": price,
                "congestion": self._pick_congestion(rec),
                "loss": self._pick_loss(rec),
                "created_at": datetime.utcnow().isoformat(),
            })
        return out

    async def get_available_nodes(self, iso: str, sample_days: int = 3, limit: int = 20000) -> List[Dict]:
        iso = iso.upper()
        info = self.iso_datasets.get(iso)
        if not info:
            logger.error(f"ISO {iso} not supported")
            return []

        dataset = info["lmp_hourly_da"]

        # Try metadata first
        meta_url = f"{self.base_url}/v1/datasets/{dataset}/metadata"
        r = await self._rate_limited_get(meta_url, params={})
        nodes: List[Dict] = []
        if r.status_code == 200:
            payload = r.json()
            locs = payload.get("locations")
            if isinstance(locs, list):
                for loc in locs:
                    code = loc.get("name") or loc.get("code") or loc.get("id")
                    if code:
                        nodes.append({
                            "node_code": code,
                            "node_name": loc.get("display_name", code),
                            "iso": iso,
                            "type": loc.get("type", "location"),
                            "source": "metadata",
                        })
            if not nodes:
                cols = payload.get("columns", {})
                for key in ("location_name", "location", "pnode_name", "settlement_point", "name"):
                    vals = (cols.get(key, {}) or {}).get("values") or (cols.get(key, {}) or {}).get("enum")
                    if isinstance(vals, list):
                        for code in vals:
                            nodes.append({
                                "node_code": code,
                                "node_name": code,
                                "iso": iso,
                                "type": "location",
                                "source": "metadata",
                            })
            if nodes:
                seen = set()
                uniq = []
                for n in nodes:
                    c = n["node_code"]
                    if c not in seen:
                        seen.add(c)
                        uniq.append(n)
                logger.info(f"Found {len(uniq)} nodes for {iso} via metadata.")
                return uniq

        logger.info(f"Metadata unavailable for {iso} ({r.status_code}); sampling recent data...")

        # Sample recent DA rows and dedupe likely keys
        end = datetime.utcnow()
        start = end - timedelta(days=sample_days)
        query_url = f"{self.base_url}/v1/datasets/{dataset}/query"
        params = {
            "start_time": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_time": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "timezone": "market",
            "limit": limit,
        }
        r = await self._rate_limited_get(query_url, params)
        if r.status_code != 200:
            logger.error(f"Sampling error {r.status_code}: {r.text[:300]}")
            return []

        likely_keys = ("location_name", "location", "pnode_name", "settlement_point", "name")
        distinct = []
        seen = set()
        for rec in r.json().get("data", []):
            for k in likely_keys:
                v = rec.get(k)
                if v:
                    v = str(v).strip()
                    if v and v not in seen:
                        seen.add(v)
                        distinct.append({
                            "node_code": v,
                            "node_name": v,
                            "iso": iso,
                            "type": "location",
                            "source": "sample",
                        })
                    break
        logger.info(f"Found {len(distinct)} nodes for {iso} via sampling.")
        return distinct

    async def get_latest_prices(self, node: str) -> Dict:
        try:
            now = datetime.utcnow()
            last_hour = now.replace(minute=0, second=0, microsecond=0)
            da = await self.fetch_day_ahead_prices(node, now)
            rt = await self.fetch_real_time_prices(node, last_hour - timedelta(hours=1), last_hour)
            latest_da = None
            if da:
                current_hour_iso = last_hour.isoformat()
                latest_da = next((p for p in da if p["hour_start"] >= current_hour_iso), da[-1])
            latest_rt = rt[-1] if rt else None
            return {
                "node": self._normalize_node(self._get_iso_from_node(node), node),
                "day_ahead": latest_da,
                "real_time": latest_rt,
                "timestamp": now.isoformat(),
            }
        except Exception as e:
            logger.error(f"get_latest_prices error: {e}")
            return {
                "node": node,
                "day_ahead": None,
                "real_time": None,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }

gridstatus_service = GridStatusAPIService()