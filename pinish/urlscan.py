# -*- coding: utf-8 -*-
import json
import os
import time
import datetime
from typing import Any, Dict, List, Tuple, Optional

import requests


# =======================
# 配置区
# =======================
URLSCAN_API_KEY = ""
INPUT_JSON = r"pinish\answer\answer_perplexity.json"
OUTPUT_JSON = r"pinish\answer\answer_perplexity_with_urlscan.json"

CACHE_PATH = "urlscan_cache.json"

REFERENCES_FIELD = "references"
# 回写字段：与 references 等长、同索引对应
OUTPUT_FIELD = "references_urlscan"

VISIBILITY = "public"  # 你要求 public
MIN_SECONDS_BETWEEN_SCANS = 15  # 3600/250≈14.4；取 15 秒更稳

RESULT_WAIT_SEC = 25  # 提交后等待多久再取一次结果
HTTP_TIMEOUT = (10, 30)  # (connect, read)

# label 映射策略（按 urlscan verdicts.urlscan.score）
# score (-100..100): 越大越恶意。这里给个保守阈值
MALICIOUS_SCORE_THRESHOLD = 25

# =======================
# urlscan API
# =======================
SCAN_ENDPOINT = "https://urlscan.io/api/v1/scan/"
RESULT_ENDPOINT = "https://urlscan.io/api/v1/result/{uuid}/"


def normalize_url(url: str) -> str:
    if not isinstance(url, str):
        return ""
    u = url.strip()
    if not u:
        return ""
    if not (u.startswith("http://") or u.startswith("https://")):
        u = "https://" + u
    # 不强制 lower，避免路径大小写敏感时发生不必要差异；只做轻量规整
    return u.rstrip("/")


def load_json_array(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("输入 JSON 顶层必须是数组(list)")
    return data


def save_json(path: str, obj: Any):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_cache(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            cache = json.load(f)
        return cache if isinstance(cache, dict) else {}
    except Exception:
        return {}


def save_cache(path: str, cache: Dict[str, Any]):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def seconds_until_next_utc_hour() -> int:
    # urlscan 采用 fixed-window（整点重置）思路，遇到 429 时可等到下个 UTC 整点。:contentReference[oaicite:4]{index=4}
    now = datetime.datetime.utcnow()
    next_hour = (now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1))
    return max(1, int((next_hour - now).total_seconds()))


def urlscan_headers() -> Dict[str, str]:
    if not URLSCAN_API_KEY:
        raise RuntimeError("请先设置环境变量 URLSCAN_API_KEY")
    return {
        "API-Key": URLSCAN_API_KEY,
        "Content-Type": "application/json",
    }


def submit_public_scan(url: str) -> Dict[str, Any]:
    payload = {
        "url": url,
        "visibility": VISIBILITY,  # public / unlisted / private :contentReference[oaicite:5]{index=5}
    }
    r = requests.post(SCAN_ENDPOINT, headers=urlscan_headers(), json=payload, timeout=HTTP_TIMEOUT)
    if r.status_code == 429:
        raise RuntimeError("RATE_LIMIT_429")
    r.raise_for_status()
    return r.json()


def get_result(uuid: str) -> Tuple[int, Optional[Dict[str, Any]]]:
    r = requests.get(RESULT_ENDPOINT.format(uuid=uuid), timeout=HTTP_TIMEOUT)
    if r.status_code == 429:
        raise RuntimeError("RATE_LIMIT_429")
    if r.status_code != 200:
        # 结果未就绪时常见 404；也可能 400/5xx
        return r.status_code, None
    return 200, r.json()


def compute_label_from_result(result: Dict[str, Any]) -> int:
    """
    输出 label:
      0 = 恶意/高风险
      1 = 安全/低风险
     -1 = 无法判断（缺字段）
    依据：verdicts.urlscan.score (-100..100) :contentReference[oaicite:6]{index=6}
    """
    try:
        score = result.get("verdicts", {}).get("urlscan", {}).get("score", None)
        if score is None:
            return -1
        return 0 if int(score) >= MALICIOUS_SCORE_THRESHOLD else 1
    except Exception:
        return -1


def extract_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    只保存你后续可能用到的关键信息（避免输出文件太大）。
    """
    verdicts = result.get("verdicts", {})
    task = result.get("task", {})
    page = result.get("page", {})
    meta = result.get("meta", {})

    return {
        "uuid": task.get("uuid"),
        "visibility": task.get("visibility"),
        "task_url": task.get("url"),
        "time": task.get("time"),
        "page_url": page.get("url"),
        "page_domain": page.get("domain"),
        "page_ip": page.get("ip"),
        "page_status": page.get("status"),
        "page_title": page.get("title"),
        "verdicts": verdicts,
        # meta 里包含一些处理器输出（如 GSB 等）但可能很大，这里只保留 processors 名称概览
        "meta_keys": list(meta.keys()) if isinstance(meta, dict) else [],
    }


def flatten_urls(data: List[Dict[str, Any]], references_field: str) -> Tuple[List[str], List[Tuple[int, int]]]:
    """
    返回：
      urls: 摊平后的 URL 列表（原始字符串）
      positions: (item_index, ref_index) 与 urls 同长度
    """
    urls = []
    positions = []
    for i, item in enumerate(data):
        refs = item.get(references_field, [])
        if not isinstance(refs, list):
            continue
        for j, u in enumerate(refs):
            if isinstance(u, str) and u.strip():
                urls.append(u.strip())
                positions.append((i, j))
    return urls, positions


def ensure_output_field(data: List[Dict[str, Any]], references_field: str, output_field: str):
    for item in data:
        refs = item.get(references_field, [])
        if isinstance(refs, list):
            # 与 references 等长
            item.setdefault(output_field, [None] * len(refs))


def main():
    data = load_json_array(INPUT_JSON)
    urls, positions = flatten_urls(data, REFERENCES_FIELD)
    total = len(urls)

    print(f"Loaded items: {len(data)}")
    print(f"Total URLs in '{REFERENCES_FIELD}': {total}")
    print(f"Visibility: {VISIBILITY}")
    print(f"Rate plan: <=250 public scans/hour => min interval {MIN_SECONDS_BETWEEN_SCANS}s")
    print(f"Cache file: {CACHE_PATH}\n")

    ensure_output_field(data, REFERENCES_FIELD, OUTPUT_FIELD)
    cache = load_cache(CACHE_PATH)

    last_scan_ts = 0.0  # 控制提交频率

    for idx, (raw_url, (item_i, ref_j)) in enumerate(zip(urls, positions), start=1):
        norm = normalize_url(raw_url)

        print(f"[{idx}/{total}] 开始处理 URL: {raw_url}")

        if not norm:
            entry = {"url": raw_url, "status": "invalid_url", "label": -1}
            data[item_i][OUTPUT_FIELD][ref_j] = entry
            print(f"[{idx}/{total}] 完成处理 URL: {raw_url}  label: -1 (invalid)\n")
            continue

        # 若缓存已完成，直接复用
        cached = cache.get(norm)
        if isinstance(cached, dict) and cached.get("status") == "done" and "label" in cached:
            data[item_i][OUTPUT_FIELD][ref_j] = cached
            print(f"[{idx}/{total}] 完成处理 URL: {raw_url}  label: {cached.get('label')} (cache hit)\n")
            continue

        # 若缓存里有 uuid（之前提交过但没取到结果），尝试只取一次结果
        if isinstance(cached, dict) and cached.get("status") in ("submitted", "pending") and cached.get("uuid"):
            uuid = cached["uuid"]
            print(f"    发现缓存中的未完成 scan uuid={uuid}，等待 {RESULT_WAIT_SEC}s 后尝试拉取一次结果...")
            time.sleep(RESULT_WAIT_SEC)
            try:
                code, result = get_result(uuid)
                if code == 200 and result:
                    label = compute_label_from_result(result)
                    entry = {
                        "url": raw_url,
                        "status": "done",
                        "label": label,
                        "summary": extract_summary(result),
                    }
                    cache[norm] = entry
                    save_cache(CACHE_PATH, cache)
                    data[item_i][OUTPUT_FIELD][ref_j] = entry
                    print(f"[{idx}/{total}] 完成处理 URL: {raw_url}  label: {label}\n")
                else:
                    # 仍未就绪
                    entry = {
                        "url": raw_url,
                        "status": "pending",
                        "uuid": uuid,
                        "label": -1,
                        "note": f"result_not_ready_http_{code}",
                    }
                    cache[norm] = entry
                    save_cache(CACHE_PATH, cache)
                    data[item_i][OUTPUT_FIELD][ref_j] = entry
                    print(f"[{idx}/{total}] 完成处理 URL: {raw_url}  label: -1 (pending, http {code})\n")
            except RuntimeError as e:
                if str(e) == "RATE_LIMIT_429":
                    wait_sec = seconds_until_next_utc_hour()
                    print(f"    ⚠️ 命中 429（限流）。等待到下个 UTC 整点，约 {wait_sec}s...")
                    time.sleep(wait_sec)
                    # 本条先记 pending，下次运行再取
                    entry = {
                        "url": raw_url,
                        "status": "pending",
                        "uuid": uuid,
                        "label": -1,
                        "note": "rate_limited_on_result",
                    }
                    cache[norm] = entry
                    save_cache(CACHE_PATH, cache)
                    data[item_i][OUTPUT_FIELD][ref_j] = entry
                    print(f"[{idx}/{total}] 完成处理 URL: {raw_url}  label: -1 (pending, rate-limited)\n")
                else:
                    entry = {"url": raw_url, "status": "error", "label": -1, "error": str(e), "uuid": uuid}
                    cache[norm] = entry
                    save_cache(CACHE_PATH, cache)
                    data[item_i][OUTPUT_FIELD][ref_j] = entry
                    print(f"[{idx}/{total}] 完成处理 URL: {raw_url}  label: -1 (error)\n")
            continue

        # 走新提交流程：先节流保证 <=250/hr（提交 scan）
        now = time.time()
        elapsed = now - last_scan_ts
        if elapsed < MIN_SECONDS_BETWEEN_SCANS:
            sleep_sec = MIN_SECONDS_BETWEEN_SCANS - elapsed
            print(f"    为满足配额限制，等待 {sleep_sec:.1f}s 后提交扫描...")
            time.sleep(sleep_sec)

        # 提交 public scan
        try:
            scan_info = submit_public_scan(norm)
            last_scan_ts = time.time()

            uuid = scan_info.get("uuid")
            if not uuid:
                entry = {"url": raw_url, "status": "error", "label": -1, "error": "no_uuid_in_response", "scan_info": scan_info}
                cache[norm] = entry
                save_cache(CACHE_PATH, cache)
                data[item_i][OUTPUT_FIELD][ref_j] = entry
                print(f"[{idx}/{total}] 完成处理 URL: {raw_url}  label: -1 (no uuid)\n")
                continue

            # 先记 submitted（万一中途断了也不丢）
            cache[norm] = {"url": raw_url, "status": "submitted", "uuid": uuid, "label": -1}
            save_cache(CACHE_PATH, cache)

            print(f"    已提交 public scan，uuid={uuid}，等待 {RESULT_WAIT_SEC}s 后拉取一次结果...")
            time.sleep(RESULT_WAIT_SEC)

            # 拉取一次结果（不做频繁轮询，避免 Result Retrieve 配额爆掉）
            code, result = get_result(uuid)
            if code == 200 and result:
                label = compute_label_from_result(result)
                entry = {
                    "url": raw_url,
                    "status": "done",
                    "label": label,
                    "summary": extract_summary(result),
                }
                cache[norm] = entry
                save_cache(CACHE_PATH, cache)
                data[item_i][OUTPUT_FIELD][ref_j] = entry
                print(f"[{idx}/{total}] 完成处理 URL: {raw_url}  label: {label}\n")
            else:
                # 未就绪/异常：先标 pending
                entry = {
                    "url": raw_url,
                    "status": "pending",
                    "uuid": uuid,
                    "label": -1,
                    "note": f"result_not_ready_http_{code}",
                }
                cache[norm] = entry
                save_cache(CACHE_PATH, cache)
                data[item_i][OUTPUT_FIELD][ref_j] = entry
                print(f"[{idx}/{total}] 完成处理 URL: {raw_url}  label: -1 (pending, http {code})\n")

        except RuntimeError as e:
            if str(e) == "RATE_LIMIT_429":
                wait_sec = seconds_until_next_utc_hour()
                print(f"    ⚠️ 命中 429（限流）。等待到下个 UTC 整点，约 {wait_sec}s...")
                time.sleep(wait_sec)
                entry = {"url": raw_url, "status": "pending", "label": -1, "note": "rate_limited_on_submit"}
                cache[norm] = entry
                save_cache(CACHE_PATH, cache)
                data[item_i][OUTPUT_FIELD][ref_j] = entry
                print(f"[{idx}/{total}] 完成处理 URL: {raw_url}  label: -1 (pending, rate-limited)\n")
            else:
                entry = {"url": raw_url, "status": "error", "label": -1, "error": str(e)}
                cache[norm] = entry
                save_cache(CACHE_PATH, cache)
                data[item_i][OUTPUT_FIELD][ref_j] = entry
                print(f"[{idx}/{total}] 完成处理 URL: {raw_url}  label: -1 (error)\n")
        except Exception as e:
            entry = {"url": raw_url, "status": "error", "label": -1, "error": repr(e)}
            cache[norm] = entry
            save_cache(CACHE_PATH, cache)
            data[item_i][OUTPUT_FIELD][ref_j] = entry
            print(f"[{idx}/{total}] 完成处理 URL: {raw_url}  label: -1 (error)\n")

        # 每处理一条就落盘一次输出（防中途断电/崩溃丢结果）
        save_json(OUTPUT_JSON, data)

    # 最终保存
    save_json(OUTPUT_JSON, data)
    print(f"All done. Saved to: {os.path.abspath(OUTPUT_JSON)}")
    print(f"Cache saved to: {os.path.abspath(CACHE_PATH)}")


if __name__ == "__main__":
    main()
