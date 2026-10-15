# 班表提醒

每天晚上 **22:00** 自动读一次班表，如果**明天**有班，就往你的企业微信群里发一条提醒。

当前规则（按你的要求）：

- 只在**有班次的日期**提醒；空白 = 休息，不提醒
- `下大夜` 是大夜班的延续日，**不提醒**
- 其余班次（晚班、晚放、白班、大夜、备份、早放）都提醒

## 文件说明

| 文件 | 作用 |
|---|---|
| `main.py` | 入口：读班表 → 找到明天的班次 → 发送 |
| `schedule.py` | 读 CSV（日期 + 班次两列，自动识别 UTF-8 / GBK 编码） |
| `notifier.py` | 往企业微信群机器人发消息 |
| `config.py` | 默认配置 + 读取 `.env` / 环境变量 |
| `config.json` | 想改行为时改这里（不含密码，可以放心提交） |
| `.env` | **本地专用，含机器人地址，绝对不要提交**（`.gitignore` 已排除） |
| `.github/workflows/remind.yml` | GitHub 上的定时规则（UTC 14:00 = 北京 22:00） |

## 本地测试（不发送）

```bash
python main.py --check              # 自检：能不能读到班表、各班次是否提醒
python main.py --preview            # 逐天列出读到的班次
python main.py --dry-run            # 只打印"明天"会发什么，不发送
python main.py --dry-run --date 2026-10-15   # 模拟 10/15 晚上会发什么
python main.py --schedule C:\path\banbiao.csv --preview   # 临时指定班表文件
