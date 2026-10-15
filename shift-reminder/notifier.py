"""把提醒发出去（企业微信群机器人）。只依赖标准库。"""

from __future__ import annotations

import json
import urllib.error
import urllib.request


def compose_message(entry, ahead_label: str = "明天") -> dict:
    date_text = f"{entry.date.month}月{entry.date.day}日 {entry.weekday_cn}"
    title = f"班表提醒：{ahead_label} {date_text} {entry.shift}"
    content = (
        f"### {ahead_label}（{date_text}）\n"
        f"**班次：{entry.shift}**\n"
        f"> 别忘了，提前安排好时间"
    )
    return {"title": title, "markdown": content}


def send_wecom(message: dict, cfg: dict) -> tuple[bool, str]:
    url = str(cfg.get("wecom_webhook_url") or "").strip()
    if not url:
        return False, "缺少 WECOM_WEBHOOK_URL（企业微信群机器人地址）"
    payload = {"msgtype": "markdown", "markdown": {"content": message["markdown"]}}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        return False, f"网络请求失败：{exc}"
    try:
        result = json.loads(body)
    except json.JSONDecodeError:
        return False, f"返回内容看不懂：{body[:200]}"
    if result.get("errcode") == 0:
        return True, "已发送到企业微信"
    return False, f"企业微信返回：{result}"


def send(message: dict, cfg: dict) -> list[tuple[str, bool, str]]:
    channel = str(cfg.get("channel") or "wecom").strip().lower()
    if channel == "none":
        return [("none", True, "已跳过发送（channel=none）")]
    if channel == "wecom":
        ok, detail = send_wecom(message, cfg)
        return [("wecom", ok, detail)]
    return [(channel, False, f"未知通道「{channel}」，目前只支持 wecom 或 none")]
