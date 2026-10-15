"""配置：默认值 -> config.json -> .env（本地）/ 环境变量（GitHub Secrets）。

班表格式（banbiao.csv）：
    date,shift
    2026/10/1,
    2026/10/2,晚班
"""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_CONFIG = {
    # 班表文件：CSV 或 XLSX 都行，相对路径按本文件所在目录解析
    "schedule_file": "banbiao.csv",
    # CSV 编码，留空=自动探测（先试 UTF-8，失败再试 GB18030/GBK）
    "csv_encoding": "",
    # 这些班次不需要提醒（下大夜 = 大夜的延续日，跨到第二天了，不算新的一天上班）
    "skip_shifts": ["下大夜"],
    # 提前几天提醒（1 = 今晚提醒明天）
    "remind_days_ahead": 1,
    # 提醒时刻，仅用于文案和日志；真正的定时在 .github/workflows/remind.yml
    "remind_at": "22:00",
    # 通知通道：wecom / none
    "channel": "wecom",
    # 北京时间
    "timezone_offset_hours": 8,
}


def load_env_file(path: Path) -> None:
    """读 .env（不覆盖已存在的环境变量）。"""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_config(root: Path | None = None) -> dict:
    root = root or Path(__file__).resolve().parent
    load_env_file(root / ".env")

    cfg = dict(DEFAULT_CONFIG)
    cfg_file = root / "config.json"
    if cfg_file.is_file():
        try:
            user = json.loads(cfg_file.read_text(encoding="utf-8-sig"))
            if isinstance(user, dict):
                for key, value in user.items():
                    if not key.startswith("_"):
                        cfg[key] = value
        except json.JSONDecodeError as exc:
            raise SystemExit(f"config.json 格式有误：{exc}")

    for env_name, key in (
        ("SCHEDULE_FILE", "schedule_file"),
        ("CSV_ENCODING", "csv_encoding"),
        ("CHANNEL", "channel"),
        ("REMIND_AT", "remind_at"),
        ("WECOM_WEBHOOK_URL", "wecom_webhook_url"),
    ):
        value = (os.environ.get(env_name) or "").strip()
        if value:
            cfg[key] = value
    cfg.setdefault("wecom_webhook_url", "")
    return cfg
