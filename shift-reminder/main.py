"""命令行入口：读班表 -> 找到目标日期的班次 -> 发提醒。

本地用法（Windows，双击 测试-不发送.bat 也行）：
    python main.py --dry-run                    # 只打印，不发送
    python main.py --preview                    # 列出整月每天读到的班次
    python main.py --dry-run --date 2026-10-15   # 模拟 10/15 晚上该发什么
    python main.py --check                      # 自检
    python main.py --send                       # 真发（默认目标=明天）

云端（GitHub Actions）用法：
    python main.py --send
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Windows 控制台默认 GBK，输出中文/符号会报编码错误
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import notifier  # noqa: E402
import schedule as sched  # noqa: E402
from config import load_config  # noqa: E402


def now_local(cfg: dict) -> dt.datetime:
    offset = float(cfg.get("timezone_offset_hours", 8))
    return dt.datetime.now(dt.timezone.utc).astimezone(dt.timezone(dt.timedelta(hours=offset)))


def parse_target(value: str | None, cfg: dict) -> dt.date:
    today = now_local(cfg).date()
    if not value:
        return today + dt.timedelta(days=int(cfg.get("remind_days_ahead", 1)))
    value = value.strip().lower()
    if value in {"today", "今天"}:
        return today
    if value in {"tomorrow", "明天"}:
        return today + dt.timedelta(days=1)
    day = sched.parse_date(value)
    if day is None:
        raise SystemExit(f"看不懂的日期：{value}（示例：2026-10-15、10/15、tomorrow）")
    return day


def ahead_label(target: dt.date, cfg: dict) -> str:
    delta = (target - now_local(cfg).date()).days
    return {0: "今天", 1: "明天", 2: "后天"}.get(delta, f"{delta}天后" if delta > 0 else "这天")


def schedule_path_for(cfg: dict) -> Path:
    raw = str(cfg.get("schedule_file") or "banbiao.csv")
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def cmd_preview(entries: list[sched.DayEntry]) -> int:
    print(f"== 班表读出来的全部内容（共 {len(entries)} 天）==")
    for entry in entries:
        mark = "—" if entry.is_off else "班"
        print(f"{entry.date} {entry.weekday_cn}  [{mark}]  {entry.summary}")
    return 0


def cmd_check(cfg: dict, path: Path) -> int:
    print("== 自检 ==")
    print(f"当前时间（UTC+{cfg.get('timezone_offset_hours', 8)}）：{now_local(cfg):%Y-%m-%d %H:%M:%S}  {sched.WEEKDAY_CN[now_local(cfg).weekday()]}")
    print(f"班表文件：{path}  {'[存在]' if path.is_file() else '[不存在]'}")
    print(f"提醒时刻：{cfg.get('remind_at')}｜提前 {cfg.get('remind_days_ahead')} 天｜通道：{cfg.get('channel')}")

    issues: list[str] = []
    if not path.is_file():
        issues.append("班表文件不存在")
        for issue in issues:
            print(f"  ! {issue}")
        return 1

    entries = sched.read_entries(path, cfg)
    dates = [e.date for e in entries]
    work = [e for e in entries if not e.is_off]
    print(f"读出 {len(entries)} 天：{min(dates)} ~ {max(dates)}；其中有班次 {len(work)} 天")
    print("各班次出现次数：")
    counts: dict[str, int] = {}
    for entry in work:
        counts[entry.shift] = counts.get(entry.shift, 0) + 1
    for shift, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        will = "会提醒" if sched.needs_reminder(next(e for e in work if e.shift == shift), cfg)[0] else "会跳过"
        print(f"  {shift} × {count}  ({will})")
    if not cfg.get("wecom_webhook_url"):
        issues.append("没有 WECOM_WEBHOOK_URL：本地没写 .env，或云端没配 Secrets")
    if issues:
        print("\n需要注意：")
        for issue in issues:
            print(f"  ! {issue}")
        return 1
    print("\n自检通过 ✅")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="班表提醒：晚上 22:00 提醒明天的班次")
    parser.add_argument("--date", help="模拟某一天晚上发出的提醒（如 2026-10-15）")
    parser.add_argument("--send", action="store_true", help="真的发送")
    parser.add_argument("--dry-run", action="store_true", help="只打印不发送（默认行为）")
    parser.add_argument("--preview", action="store_true", help="列出整月读到的班次")
    parser.add_argument("--check", action="store_true", help="自检")
    parser.add_argument("--schedule", help="临时指定班表文件路径（不写 config）")
    args = parser.parse_args(argv)

    cfg = load_config(ROOT)
    if args.schedule:
        cfg["schedule_file"] = args.schedule
    path = schedule_path_for(cfg)

    if args.check:
        return cmd_check(cfg, path)

    entries = sched.read_entries(path, cfg)
    if args.preview:
        return cmd_preview(entries)

    target = parse_target(args.date, cfg)
    label = ahead_label(target, cfg)
    entry = sched.find_entry(entries, target)

    print(f"[信息] 班表：{path.name}｜读出 {len(entries)} 天")
    print(f"[信息] 目标日期：{target} {sched.WEEKDAY_CN[target.weekday()]}（{label}）")

    if entry is None:
        print("[跳过] 班表里没有这一天")
        return 0

    should, reason = sched.needs_reminder(entry, cfg)
    if not should:
        print(f"[跳过] {reason}")
        return 0

    message = notifier.compose_message(entry, label)
    if not args.send:
        print("\n--- 如果现在发送，群里会出现 ---")
        print(message["markdown"])
        print("\n[dry-run] 没有发送。")
        return 0

    results = notifier.send(message, cfg)
    failed = False
    for name, ok, detail in results:
        print(f"[{'成功' if ok else '失败'}] {name}: {detail}")
        failed = failed or not ok
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
