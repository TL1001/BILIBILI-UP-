#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""BiliWatch —— B 站关注 UP 更新监控（单文件版）
====================================================================

把关注的 UP 主的最新投稿抓下来，生成 Obsidian Markdown 笔记（每个 UP 一篇 +
分区笔记 + 总览页 + 收藏夹.md）。只产出 Markdown，不生成任何 Word 文档。

本文件是原 bilisync 包（19 个模块、约 5100 行）按依赖拓扑序合并成的单文件：
包内 `from .xxx import yyy` 的跨模块引用已全部改写为同文件内的直接引用，
重复的顶层 import 已合并到文件头，跨模块同名符号已加前缀区分。
因此不需要包目录、不需要 pip install 本项目 —— 单独拷走这一个 .py 就能跑。

一、环境要求
--------------------------------------------------------------------
    Python 3.11+（用到标准库 tomllib）；实测 3.13.14 可用。
    Windows / macOS / Linux 均可运行；schedule（定时任务）命令仅支持 Windows。

二、依赖安装（只需一次）
--------------------------------------------------------------------
    pip install playwright
    python -m playwright install chromium

    · playwright       唯一必需依赖（驱动 Chromium 访问 B 站）
    国内网络慢可换镜像：
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple playwright
    若镜像报 "from versions: none"，改用官方源：
    pip install -i https://pypi.org/simple playwright

    注意：playwright 是「用到才导入」。没装时仍然可以跑
    `--help`、`doctor`、`migrate --dry-run`，只有真正启动浏览器时才报缺包。

三、运行方式
--------------------------------------------------------------------
    最省事：直接双击 `Bili.exe` 或本文件（分步交互版：选浏览器模式 → 自检 →
    选任务范围，未登录才弹窗扫码）。命令行不带参数运行也走同一套向导：
        python "BiliWatch_单文件版.py"

    也可以显式指定命令。
    首次使用（会弹浏览器，用手机 B 站 App 扫码）：
        python "BiliWatch_单文件版.py" login

    之后每次抓取：
        python "BiliWatch_单文件版.py" run

    常用组合：
        run --show               显示浏览器窗口（能看见它在做什么）
        run --limit 5            只处理前 5 个 UP，先试水
        run --dry-run            只抓取不写文件
        run --only 12345,6789    只更新指定 mid 的 UP
        favs                     只抓收藏夹（写 收藏夹.md）
        favs --no-covers         收藏夹不下载封面

    全部命令：
        run         抓取并写入 Markdown 笔记
        login       扫码登录并保存登录态
        followings  只抓关注名单到 followings.txt
        favs        抓取 B 站收藏夹，生成「收藏夹.md」
        zones       为关注 UP 批量标注分区
        migrate     整理笔记目录结构、修链接
        schedule    安装 / 查看 / 删除 Windows 定时任务
        doctor      环境自检（会启动一次浏览器验证登录态）

    单个命令看全部参数：
        python "BiliWatch_单文件版.py" run --help

四、运行时数据放在哪
--------------------------------------------------------------------
    默认在脚本同级的 BiliWatch_数据\ 目录：
        config.toml        配置（首次运行自动生成，可直接编辑）
        state.json         去重记录：哪些视频已经抓过
        .profile\          浏览器登录态（扫码一次，之后免登录）
        logs\              运行日志（run-*.log / watchdog.log / errors.log）
        followings.txt     关注名单缓存
        run-silent.bat     定时任务用的静默启动脚本（自动生成）

    换位置：设置环境变量 BILIWATCH_HOME 指向目标目录。
    脚本所在目录不可写时，自动退到 %LOCALAPPDATA%\BiliWatch。

五、输出到哪里
--------------------------------------------------------------------
    笔记：%USERPROFILE%\Documents\B站关注更新\Obsidian库\08_B站关注\
            |-- B站关注总览.md
            |-- B站UP文件夹\<分区>\<UP名>.md
            |-- 收藏夹.md
            |-- _assets\covers、avatars

    不装 Obsidian 也能用：笔记就是普通 .md 文件，目录不存在会逐级自动创建。
    以上路径都在 config.toml 里改，支持 %VAR% 与 ~。

六、文件结构（按依赖顺序展开，共 20 节）
--------------------------------------------------------------------
     1  运行时目录、内置默认配置、依赖懒加载     ← 原 __main__ 装配逻辑
     2  config      配置解析与路径展开
     3  wbi         B 站接口签名（w_rid）
     4  zone        视频分区判定
     5  state       运行状态与去重
     6  controls    按 P 暂停 / R 继续
     7  watchdog    卡死检测与强制续跑
     8  detect      Obsidian 探测
     9  output      目录准备与安全写盘
    10  notes       笔记 Markdown 渲染
    11  migrate     笔记目录整理与链接修复
    12  browser     Playwright 浏览器封装
    13  scrape      UP 视频列表抓取
    14  pool        多实例并发调度
    15  favs        收藏夹抓取
    16  followlist  关注名单抓取
    17  pipeline    主流程编排
    18  cli         命令行入口
    19  probe       页面结构探针（开发调试）
    20  入口        __main__

七、注意事项
--------------------------------------------------------------------
    · 同一时间只跑一个实例：两个进程会抢同一个 .profile 登录目录。
    · 抓取之间默认随机等待 3~6 秒/UP，是节流避免风控，别调太小。
    · 卡住不动超过 180 秒，看门狗会强制重启并续跑（退出码 9），日志里有记录。
    · 出问题先跑 doctor，它会说明缺什么。
    · 双击运行时如果自检没过/程序报错，窗口会停住等按键，不再一闪而过；
      本次运行的完整输出在 <数据目录>\logs\latest.log（带时间戳的历史同目录），
      崩溃堆栈另存 crash-*.log。从 cmd 或定时任务里跑不会停，
      需要时可用 BILIWATCH_NO_HOLD=1 强制关掉驻留。
    · 与原包的行为差异仅三处，均为消除重名 / 让单文件可独立运行：
        output.describe → 保持原名；zone.describe → describe_zone
        probe.UA → PROBE_UA；probe.main → probe_main
      模块内的业务逻辑一行未改。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import queue
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import traceback
import urllib.parse

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page

# ════════════════════════════════════════════════════════════════════
# 01 / 20 · 装配 —— 运行时目录、内置默认配置、依赖懒加载（原 __main__ 装配逻辑）
#    （原文件：bilisync/__main__.py 的运行期装配 + config.toml 默认值）
# ════════════════════════════════════════════════════════════════════


APP_NAME = "BiliWatch 单文件版"
__version__ = "2.0.0"

# 原包把 config.toml / state.json / logs 放在「项目根」，单文件版把它们放在
# 数据目录（默认脚本同级 BiliWatch_数据）。下面这个函数决定数据目录在哪。
_DATA_DIRNAME = "BiliWatch_数据"


def _resolve_home() -> Path:
    """数据目录：环境变量 BILIWATCH_HOME > 脚本同级 > %LOCALAPPDATA%\\BiliWatch。"""
    env = os.environ.get("BILIWATCH_HOME", "").strip()
    candidates = []
    if env:
        candidates.append(Path(os.path.expandvars(os.path.expanduser(env))).resolve())
    # PyInstaller --onefile 下 __file__ 指向临时解压目录，exe 要用 exe 自己所在目录
    if getattr(sys, "frozen", False):
        here = Path(sys.executable).resolve().parent
    else:
        here = Path(os.path.abspath(__file__)).resolve().parent
    candidates.append(here / _DATA_DIRNAME)
    candidates.append(Path(os.environ.get("LOCALAPPDATA") or here) / "BiliWatch")

    errors = []
    for cand in candidates:
        try:
            cand.mkdir(parents=True, exist_ok=True)
            probe = cand / ".wb_write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return cand
        except Exception as exc:
            errors.append(f"{cand}：{exc}")
    # 所有候选目录都建不起来时**不能直接退出**：双击 exe 时窗口属于进程，
    # 抛 SystemExit 等于「闪一下就没了」，用户连错误都读不到。
    # 退到临时目录，先让程序跑起来、把日志写下来。
    import tempfile as _tf

    fallback = Path(_tf.gettempdir()) / _DATA_DIRNAME
    print("[警告] 无法在脚本目录/用户目录创建数据目录，本次临时改用：%s" % fallback)
    for line in errors:
        print("        " + line)
    try:
        fallback.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return fallback


PROJECT_ROOT = _resolve_home()
DEFAULT_CONFIG = PROJECT_ROOT / "config.toml"
STATE_FILE = PROJECT_ROOT / "state.json"
DEFAULT_CONFIG_TEXT = r'''# B站关注 UP 更新监控 —— 配置文件
# 修改后无需重新安装，下次运行即生效。

[vault]
# Obsidian 库根目录。
# 注意：路径不存在也没关系，运行时会把整条目录链自动建出来（父级全部补齐）；
#       装不装 Obsidian 都不影响写笔记 —— 笔记就是普通 Markdown 文件。
# 支持 %VAR% 与 ~，换机器不用改。
root = "%USERPROFILE%/Desktop/B站关注更新/Obsidian库"
# 笔记写入位置（就是库根目录本身；也可指向已有 Obsidian 库里的某个子文件夹）
notes_root = "%USERPROFILE%/Desktop/B站关注更新/Obsidian库"
# 子目录：整个 B 站分区放在这里（下面三行都是相对它的路径）
up_dir = "08_B站关注"
# UP 笔记子文件夹：其下再按「分区」分子文件夹，每个 UP 一篇笔记
# 目录层级：08_B站关注/B站关注总览.md + 08_B站关注/收藏夹.md
#          + 08_B站关注/B站UP文件夹/<分区>/*.md + 08_B站关注/_assets/
ups_subdir = "B站UP文件夹"
# 封面/头像附件目录（相对 up_dir）
assets_subdir = "_assets"
# 总览页文件名（相对 up_dir）
index_note = "B站关注总览.md"

[scrape]
# 每个 UP 抓取多少条最新视频
videos_per_up = 5
# 最多处理多少个 UP（0 = 全部关注）
max_ups = 0
# 每个 UP 之间的随机等待区间（秒），相当于节流，别调太小
delay_min = 3.0
delay_max = 6.0
# 无头模式；向导里选「前台运行」会传 --show 覆盖为有窗口（可实时观看），定时任务保持无头
headless = true
# 单页超时（毫秒）
timeout_ms = 45000
# 看门狗：超过这么多秒没有任何进展，就判定卡死、强杀并自动续跑
watchdog_seconds = 180
# 并发浏览器实例数：多个实例同时抓不同 UP，速度约提升为 N 倍。
# 单个实例卡死只会被单独重启，不影响其他实例。1 = 退化为单线程。
# 建议 2~4：太大容易触发 B 站风控（空列表增多）。
workers = 3
# 关注列表缓存天数，超过则重新抓取
refresh_followings_days = 7
# 是否下载头像
download_avatars = true

[favs]
# 收藏夹笔记（收藏夹.md）的展示选项
# 是否下载并嵌入视频封面缩略图。封面存到 _assets/covers/BVxxx.jpg，
# 与 UP 笔记共用同一份，已存在的不重复下载。
with_covers = true
# 缩略图显示宽度（像素）。想排成一列小图就调小（如 200），设为 0 则不显示封面。
cover_width = 320

[profile]
# 浏览器持久化配置目录（保存登录 cookie）
dir = ".profile"

[schedule]
# 建议的执行时刻（供 schedule 命令使用，可自行修改）
times = ["09:00", "21:00"]
'''

REQUIRED_PACKAGES = [
    ("playwright", "playwright",
     "pip install playwright && python -m playwright install chromium"),
]


def _write_default_config(home: Path) -> Path:
    """config.toml 不存在时按内置默认值生成；已存在一律不动（不动用户的修改）。"""
    cfg = home / "config.toml"
    if cfg.exists():
        return cfg
    try:
        cfg.write_text(DEFAULT_CONFIG_TEXT, encoding="utf-8", newline="\n")
        print(f"[初始化] 已生成默认配置：{cfg}")
    except Exception as exc:
        raise SystemExit(
            f"[错误] 无法写入配置文件：{cfg}\n  原因：{exc}\n"
            f"  建议：检查目录是否只读，或用环境变量 BILIWATCH_HOME 换一个可写目录。"
        )
    return cfg


def _ensure_silent_bat(home: Path) -> None:
    """schedule 命令依赖 <数据目录>\\run-silent.bat，缺了就地补一个。"""
    bat = home / "run-silent.bat"
    if bat.exists():
        return
    try:
        log_dir = home / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        lines = [
            "@echo off",
            f'cd /d "{home}"',
            f'"{sys.executable}" "{os.path.abspath(__file__)}" run >> "{log_dir / "run.log"}" 2>&1',
        ]
        bat.write_text("\r\n".join(lines) + "\r\n", encoding="gbk", errors="replace")
    except Exception:
        pass  # 只影响定时任务，不影响手动运行


def _sync_playwright():
    """延迟导入 playwright：只有真正启动浏览器时才需要它。

    doctor / --help / migrate 这类不联网的命令因此不需要装 playwright 也能跑。
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise SystemExit(
            "[错误] 缺少依赖 playwright，无法启动浏览器。\n"
            "  安装：pip install playwright && python -m playwright install chromium\n"
            f"  当前 Python：{sys.version.split()[0]}（{sys.executable}）"
        ) from exc
    return sync_playwright


def _check_deps() -> bool:
    """不启动浏览器，只报告缺哪个包、怎么装。"""
    import importlib

    missing = []
    for module_name, pkg_name, hint in REQUIRED_PACKAGES:
        try:
            importlib.import_module(module_name)
        except Exception:
            missing.append((pkg_name, hint))
    if not missing:
        print("✓ 依赖齐全：playwright")
        return True

    print("=" * 62)
    for pkg, hint in missing:
        print(f"  缺少：{pkg}")
        print(f"  安装：{hint}")
    print("-" * 62)
    print(f"当前 Python：{sys.version.split()[0]}（{sys.executable}）")
    print("=" * 62)
    return False

# ════════════════════════════════════════════════════════════════════
# 02 / 20 · config —— 配置解析与路径展开（tomllib → dataclass，缺项用内置默认值兜底）
#    （原文件：bilisync/config.py）
# ════════════════════════════════════════════════════════════════════

# PROJECT_ROOT / DEFAULT_CONFIG / STATE_FILE / DEFAULT_CONFIG_TEXT 已在第 1 节定义。

"""配置加载与路径解析。

设计原则：配置缺项用内置默认值兜底，避免因为少写一行 key 就直接崩。
路径统一在这里解析成 pathlib.Path，其余模块不关心相对/绝对的问题。
"""



















@dataclass
class ScrapeSettings:
    videos_per_up: int = 5
    max_ups: int = 0
    delay_min: float = 3.0
    delay_max: float = 6.0
    headless: bool = True
    timeout_ms: int = 45000
    watchdog_seconds: float = 180.0
    refresh_followings_days: int = 7
    download_avatars: bool = True
    workers: int = 3  # 并发浏览器实例数；1 = 退化为单线程


@dataclass
class VaultSettings:
    """up_dir 是「08_B站关注」这个分区根目录；ups_dir 是里面放 UP 笔记的子文件夹。

    层级（刻意保持扁平，只有一层）：
        08_B站关注/
        ├── B站关注总览.md      ← 分区入口，每次运行整篇重写
        ├── B站UP文件夹/        ← 每个 UP 一篇 .md
        └── _assets/            ← 封面、头像等附件
    """

    root: Path
    notes_root: Path
    up_dir: Path
    ups_dir: Path          # up_dir / ups_subdir
    ups_subdir: str        # 子文件夹名，参与 Obsidian 链接
    covers_dir: Path
    avatars_dir: Path
    index_note: Path


@dataclass
class FavSettings:
    """收藏夹笔记的显示选项。"""

    with_covers: bool = True   # 是否下载并嵌入封面缩略图
    cover_width: int = 320     # 缩略图显示宽度（像素），0 表示不显示


@dataclass
class Config:
    vault: VaultSettings
    scrape: ScrapeSettings
    profile_dir: Path
    profile_expanded: str  # 传给 Playwright 的 user_data_dir（已展开环境变量）
    favs: FavSettings = field(default_factory=FavSettings)
    schedule_times: list[str] = field(default_factory=lambda: ["09:00", "21:00"])
    raw: dict = field(default_factory=dict)


def _expand(value: str) -> str:
    return os.path.expandvars(os.path.expanduser(value))


def load_config(path: Path | str | None = None) -> Config:
    cfg_path = Path(path) if path else DEFAULT_CONFIG
    if not cfg_path.exists():
        raise FileNotFoundError(f"找不到配置文件：{cfg_path}")

    with cfg_path.open("rb") as fh:
        raw = tomllib.load(fh)

    v = raw.get("vault", {})
    s = raw.get("scrape", {})
    p = raw.get("profile", {})
    fv = raw.get("favs", {})

    vault_root = Path(_expand(v["root"]))
    notes_root = Path(_expand(v["notes_root"]))
    up_dir = notes_root / v.get("up_dir", "08_B站关注")
    assets = up_dir / v.get("assets_subdir", "_assets")
    ups_subdir = str(v.get("ups_subdir", "B站UP文件夹")).strip() or "B站UP文件夹"
    ups_dir = up_dir / ups_subdir

    scrape = ScrapeSettings(
        videos_per_up=int(s.get("videos_per_up", 5)),
        max_ups=int(s.get("max_ups", 0)),
        delay_min=float(s.get("delay_min", 3.0)),
        delay_max=float(s.get("delay_max", 6.0)),
        headless=bool(s.get("headless", True)),
        timeout_ms=int(s.get("timeout_ms", 45000)),
        watchdog_seconds=float(s.get("watchdog_seconds", 180)),
        refresh_followings_days=int(s.get("refresh_followings_days", 7)),
        download_avatars=bool(s.get("download_avatars", True)),
        workers=max(1, int(s.get("workers", 3))),
    )
    if scrape.delay_max < scrape.delay_min:
        scrape.delay_max = scrape.delay_min

    profile_raw = _expand(p.get("dir", ".profile"))
    profile_path = Path(profile_raw)
    if not profile_path.is_absolute():
        profile_path = PROJECT_ROOT / profile_path

    return Config(
        vault=VaultSettings(
            root=vault_root,
            notes_root=notes_root,
            up_dir=up_dir,
            ups_dir=ups_dir,
            ups_subdir=ups_subdir,
            covers_dir=assets / "covers",
            avatars_dir=assets / "avatars",
            index_note=up_dir / v.get("index_note", "B站关注总览.md"),
        ),
        scrape=scrape,
        profile_dir=profile_path,
        profile_expanded=str(profile_path),
        favs=FavSettings(
            with_covers=bool(fv.get("with_covers", True)),
            cover_width=max(0, int(fv.get("cover_width", 320))),
        ),
        schedule_times=list(raw.get("schedule", {}).get("times", ["09:00", "21:00"])),
        raw=raw,
    )

# ════════════════════════════════════════════════════════════════════
# 03 / 20 · wbi —— B 站接口签名：w_rid / wts 计算，让 space 接口不被风控
#    （原文件：bilisync/wbi.py）
# ════════════════════════════════════════════════════════════════════

"""B 站 Wbi 签名（被 favs / zone 等模块共用）。

背景：B 站大部分空间/收藏类接口已强制 Wbi 签名，不带签名会 404 或被风控拦截。
签名流程（官方前端逻辑的逆向，社区已充分验证）：
  1. nav 接口返回 wbi_img 两张图 URL，文件名分别是 img_key / sub_key；
  2. 按 B 站固定混淆表对 img_key+sub_key 重排，取前 32 位得到 mixin_key；
  3. 请求参数加 wts=当前秒，过滤 !'()* 字符，按 key 排序 urlencode；
  4. md5(query + mixin_key) 得到 w_rid，与参数一起发出。

请求全部在已登录页面内用 fetch 发起：cookie 自动携带、Referer 天然合法。
"""








_NAV_API = "https://api.bilibili.com/x/web-interface/nav"

_FETCH_JS = (
    "async (url) => { const r = await fetch(url, { credentials: 'include' }); "
    "return { status: r.status, body: await r.text() }; }"
)

# B 站 Wbi 混淆表（官方前端 JS 里的固定常量）
_MIXIN_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52,
]


def get_json(page, url: str) -> dict:
    """页面内 fetch 调 B 站接口，校验状态码与业务码，返回 data 字段。"""
    resp = page.evaluate(_FETCH_JS, url)
    if resp["status"] != 200 or not resp["body"].lstrip().startswith("{"):
        raise RuntimeError(f"接口被拦截（HTTP {resp['status']}，非 JSON 响应）：{url.split('?')[0]}")
    data = json.loads(resp["body"])
    if data.get("code") != 0:
        raise RuntimeError(f"接口返回 code={data.get('code')}（{data.get('message', '')}）")
    return data.get("data") or {}


def nav(page) -> dict:
    """登录用户信息（isLogin / mid / uname）。"""
    return get_json(page, _NAV_API)


def keys(page) -> tuple[str, str]:
    """从 nav 接口拿 Wbi 密钥（两张混淆图 URL 的文件名）。"""
    n = get_json(page, _NAV_API)
    img = n["wbi_img"]["img_url"].rsplit("/", 1)[1].split(".")[0]
    sub = n["wbi_img"]["sub_url"].rsplit("/", 1)[1].split(".")[0]
    return img, sub


def sign(params: dict, img_key: str, sub_key: str) -> dict:
    """给参数加 Wbi 签名（wts + w_rid）。"""
    mixin = "".join((img_key + sub_key)[i] for i in _MIXIN_TAB)[:32]
    p = dict(params, wts=int(time.time()))
    p = {k: "".join(ch for ch in str(v) if ch not in "!'()*") for k, v in sorted(p.items())}
    query = urllib.parse.urlencode(p)
    p["w_rid"] = hashlib.md5((query + mixin).encode()).hexdigest()
    return p


def signed_get(page, base: str, params: dict, keys_pair: tuple[str, str]) -> dict:
    """带 Wbi 签名的 GET，返回 data 字段。"""
    url = base + "?" + urllib.parse.urlencode(sign(params, *keys_pair))
    return get_json(page, url)

# ════════════════════════════════════════════════════════════════════
# 04 / 20 · zone —— 视频分区判定：BV → tid → 官方分区名
#    （原文件：bilisync/zone.py）
# ════════════════════════════════════════════════════════════════════

"""UP 主分区标注（基于 B 站官方分区体系）。

背景：B 站的官方分区挂在**稿件**上，UP 主没有"所属分区"属性；且当前
view 接口只返回分区编号（tid），分区名（tname/tname_v2）已对网页端隐藏。
因此本模块的做法是：

  1. 取 UP 最新一稿的 BV 号（state.history 里已存）；
  2. 调 /x/web-interface/view?bvid= 拿 tid（公开接口、无需签名，仅分区名被隐藏）；
  3. 用内置的官方分区表（tid → 主分区/子分区）翻译出名称。

分区表来源：B 站现行分区树（biliup.github.io/tid-ref.html 与
bilibili-toolman 项目交叉校验），tid 多年稳定；遇到未收录的 tid 会记日志、
该 UP 保持未标注（下轮运行或 --force 重试），绝不猜名字。
"""





VIEW_API = "https://api.bilibili.com/x/web-interface/view"
SPACE_VIDEO = "https://space.bilibili.com/{mid}/video"
ARC_PATH = "/x/space/wbi/arc/search"

# B 站官方分区表：tid -> (主分区, 子分区)
ZONE_TABLE: dict[int, tuple[str, str]] = {
    # 动画（主分区 1）
    1: ("动画", ""), 24: ("动画", "MAD·AMV"), 25: ("动画", "MMD·3D"),
    27: ("动画", "综合"), 47: ("动画", "短片·手书·配音"), 210: ("动画", "手办·模玩"),
    86: ("动画", "特摄"), 257: ("动画", "配音"), 253: ("动画", "动漫杂谈"),
    # 番剧（13）
    13: ("番剧", ""), 32: ("番剧", "完结动画"), 33: ("番剧", "连载动画"),
    51: ("番剧", "资讯"), 152: ("番剧", "官方延伸"),
    # 国创（167）
    167: ("国创", ""), 153: ("国创", "国产动画"), 168: ("国创", "国产原创相关"),
    169: ("国创", "布袋戏"), 170: ("国创", "资讯"), 195: ("国创", "动态漫·广播剧"),
    # 音乐（3）
    3: ("音乐", ""), 28: ("音乐", "原创音乐"), 29: ("音乐", "音乐现场"),
    30: ("音乐", "VOCALOID·UTAU"), 31: ("音乐", "翻唱"), 59: ("音乐", "演奏"),
    130: ("音乐", "音乐综合"), 193: ("音乐", "MV"), 194: ("音乐", "电音"),
    243: ("音乐", "乐评盘点"), 244: ("音乐", "音乐教学"),
    # 舞蹈（129）
    129: ("舞蹈", ""), 20: ("舞蹈", "宅舞"), 154: ("舞蹈", "舞蹈综合"),
    156: ("舞蹈", "舞蹈教程"), 198: ("舞蹈", "街舞"), 199: ("舞蹈", "明星舞蹈"),
    200: ("舞蹈", "中国舞"), 255: ("舞蹈", "手势·网红舞"),
    # 游戏（4）
    4: ("游戏", ""), 17: ("游戏", "单机游戏"), 19: ("游戏", "Mugen"),
    65: ("游戏", "网络游戏"), 121: ("游戏", "GMV"), 136: ("游戏", "音游"),
    171: ("游戏", "电子竞技"), 172: ("游戏", "手机游戏"), 173: ("游戏", "桌游棋牌"),
    # 知识（36）
    36: ("知识", ""), 122: ("知识", "野生技能协会"), 124: ("知识", "社科·法律·心理"),
    201: ("知识", "科学科普"), 207: ("知识", "财经商业"), 208: ("知识", "校园学习"),
    209: ("知识", "职业职场"), 228: ("知识", "人文历史"), 229: ("知识", "设计·创意"),
    # 科技（188）
    188: ("科技", ""), 95: ("科技", "数码"), 230: ("科技", "软件应用"),
    231: ("科技", "计算机技术"), 232: ("科技", "科工机械"), 233: ("科技", "极客DIY"),
    # 运动（234）
    234: ("运动", ""), 235: ("运动", "篮球"), 164: ("运动", "健身"),
    236: ("运动", "竞技体育"), 237: ("运动", "运动文化"), 238: ("运动", "运动综合"),
    # 汽车（223）
    223: ("汽车", ""), 176: ("汽车", "汽车生活"), 224: ("汽车", "汽车文化"),
    225: ("汽车", "汽车极客"), 240: ("汽车", "摩托车"), 226: ("汽车", "智能出行"),
    227: ("汽车", "购车攻略"),
    # 美食（211）
    211: ("美食", ""), 76: ("美食", "美食制作"), 212: ("美食", "美食侦探"),
    213: ("美食", "美食测评"), 214: ("美食", "田园美食"), 215: ("美食", "美食记录"),
    # 动物圈（217）
    217: ("动物圈", ""), 218: ("动物圈", "喵星人"), 219: ("动物圈", "汪星人"),
    220: ("动物圈", "大熊猫"), 221: ("动物圈", "野生动物"), 222: ("动物圈", "爬宠"),
    75: ("动物圈", "动物综合"),
    # 生活（160）
    160: ("生活", ""), 21: ("生活", "日常"), 138: ("生活", "搞笑"),
    239: ("生活", "家居房产"), 161: ("生活", "手工"), 162: ("生活", "绘画"),
    # 鬼畜（119）
    119: ("鬼畜", ""), 22: ("鬼畜", "鬼畜调教"), 26: ("鬼畜", "音MAD"),
    126: ("鬼畜", "人力VOCALOID"), 216: ("鬼畜", "鬼畜剧场"), 127: ("鬼畜", "教程演示"),
    # 时尚（155）
    155: ("时尚", ""), 157: ("时尚", "美妆护肤"), 158: ("时尚", "穿搭"),
    159: ("时尚", "时尚潮流"), 192: ("时尚", "风尚标"),
    # 娱乐（5）
    5: ("娱乐", ""), 71: ("娱乐", "综艺"), 137: ("娱乐", "明星"), 131: ("娱乐", "Korea相关"),
    241: ("娱乐", "娱乐杂谈"), 242: ("娱乐", "娱乐粉丝创作"),
    # 影视（181）
    181: ("影视", ""), 85: ("影视", "短片"), 182: ("影视", "影视杂谈"),
    183: ("影视", "影视剪辑"), 184: ("影视", "预告·资讯"),
    # 纪录片（177）
    177: ("纪录片", ""), 37: ("纪录片", "人文·历史"), 178: ("纪录片", "科学·探索·自然"),
    179: ("纪录片", "军事"), 180: ("纪录片", "社会·美食·旅行"),
    # 电影（23）
    23: ("电影", ""), 147: ("电影", "华语电影"), 145: ("电影", "欧美电影"),
    146: ("电影", "日本电影"), 83: ("电影", "其他国家"),
    # 电视剧（11）
    11: ("电视剧", ""), 185: ("电视剧", "国产剧"), 187: ("电视剧", "海外剧"),
    # ---- 2024 年后新增子分区（来源：B 站官方分区树，Greasyfork 分区脚本交叉校验） ----
    245: ("汽车", "赛车"), 246: ("汽车", "改装玩车"), 247: ("汽车", "新能源车"),
    248: ("汽车", "房车"), 258: ("汽车", "汽车知识科普"),
    249: ("运动", "足球"),
    250: ("生活", "出行"), 251: ("生活", "三农"), 254: ("生活", "亲子"),
    252: ("时尚", "仿妆cos"),
    256: ("影视", "短片"), 259: ("影视", "AI影像"), 260: ("影视", "影视整活"),
    261: ("影视", "影视综合"),
    262: ("娱乐", "CP安利"), 263: ("娱乐", "颜值安利"), 264: ("娱乐", "娱乐资讯"),
    265: ("音乐", "AI音乐"), 266: ("音乐", "音乐粉丝饭拍"), 267: ("音乐", "电台"),
}


def _translate(tid, bvid: str = "", log=print) -> dict | None:
    """tid → {zone, sub, bv}。分区表未收录时只记日志、不猜名字。"""
    if tid is None:
        return None
    entry = ZONE_TABLE.get(int(tid))
    if entry is None:
        log(f"[zone] {bvid or f'tid={tid}'} 的分区 tid={tid} 不在分区表中（B 站新增分区？），跳过标注")
        return None
    main, sub = entry
    return {"zone": main, "sub": sub, "bv": bvid}


def fetch_up_zone(page, bvid: str = "", mid: str = "", log=print) -> dict | None:
    """查一个 UP 的官方分区。

    优先走「最新一稿 BV → view 接口 → tid」（快、稳）；
    拿不到 BV（该 UP 从未抓成功过）时，退化为「打开空间页、拦截它自己发出的
    arc/search 响应读 typeid」——页面自带签名与风控参数，成功率更高。
    """
    if bvid:
        try:
            data = get_json(page, f"{VIEW_API}?bvid={bvid}")
            got = _translate(data.get("tid"), bvid, log)
            if got:
                return got
        except Exception as exc:
            log(f"[zone] {bvid} 分区查询失败：{exc}")
    if mid:
        return _zone_from_space(page, mid, log)
    return None


def _zone_from_space(page, mid: str, log=print) -> dict | None:
    """拦住空间页自己发的投稿列表请求，从 vlist[0].typeid 读分区。"""
    try:
        with page.expect_response(lambda r: ARC_PATH in r.url, timeout=25000) as ri:
            page.goto(SPACE_VIDEO.format(mid=mid), wait_until="domcontentloaded")
        data = ri.value.json()
        vlist = ((data.get("data") or {}).get("list") or {}).get("vlist") or []
    except Exception as exc:
        log(f"[zone] {mid} 空间页取分区失败：{type(exc).__name__}: {str(exc)[:90]}")
        return None
    if not vlist:
        return None
    got = _translate(vlist[0].get("typeid"), vlist[0].get("bvid", ""), log)
    if got:
        log(f"[zone] {mid} 分区来自空间页兜底：tid={vlist[0].get('typeid')}")
    return got


def describe_zone(info: dict | None) -> str:
    """渲染分区描述，如「游戏 · 单机游戏」；只有主分区时如「游戏」。"""
    if not info or not info.get("zone"):
        return "未知"
    sub = info.get("sub") or ""
    return f"{info['zone']} · {sub}" if sub else info["zone"]


# 主分区的官方顺序（按 ZONE_TABLE 的书写顺序去重），用于目录/总览页的分区排序，
# 保证每次生成的顺序都一样，不会因为字典顺序或拼音排序而抖动。
MAIN_ZONES: list[str] = list(dict.fromkeys(main for main, _ in ZONE_TABLE.values()))

UNZONED = "未分区"


def zone_rank(name: str) -> int:
    """分区排序权重：官方顺序，未知分区与「未分区」排最后。"""
    if name == UNZONED:
        return 900
    try:
        return MAIN_ZONES.index(name)
    except ValueError:
        return 800


def sort_zones(names) -> list[str]:
    """把一组分区名按官方顺序排好（未分区永远在最后）。"""
    return sorted(set(names), key=lambda n: (zone_rank(n), n))

# ════════════════════════════════════════════════════════════════════
# 05 / 20 · state —— 运行状态与去重：followings / ups / runs 三张表
#    （原文件：bilisync/state.py）
# ════════════════════════════════════════════════════════════════════

"""抓取状态的持久化。

存三样东西就够：
1. followings —— 关注列表缓存（含上次刷新时间，避免每次都滚一遍关注页）
2. ups        —— 每个 UP 见过的视频（用于判断"哪些是新视频"和统计更新频率）
3. runs       —— 最近若干次运行记录（写进总览页，失败也能看出来）
"""








MAX_RUNS = 30


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


class State:
    def __init__(self, path: Path | str, data: dict | None = None):
        self.path = Path(path)
        self.data = data or {"version": 1, "followings": {"refreshed_at": None, "items": []}, "ups": {}, "runs": []}
        self.last_save_error: str | None = None  # 最近一次落盘失败原因（None = 正常）

    # ---------- 读写 ----------

    @classmethod
    def load(cls, path: Path | str) -> "State":
        p = Path(path)
        if not p.exists():
            return cls(p)
        try:
            with p.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            # 状态文件损坏不该让整次抓取失败，降级为空状态并保留坏文件
            broken = p.with_suffix(".broken.json")
            try:
                p.replace(broken)
            except OSError:
                pass
            print(f"[warn] state.json 无法解析（{exc}），已备份为 {broken.name}，本次按空状态运行")
            return cls(p)
        data.setdefault("followings", {"refreshed_at": None, "items": []})
        data.setdefault("ups", {})
        data.setdefault("fav_ups", {})
        data.setdefault("runs", [])
        return cls(p, data)

    def save(self) -> None:
        """原子落盘。失败（磁盘满/被占用/只读）只记录原因，绝不抛出去打崩整轮抓取。"""
        tmp = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(self.data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
            self.last_save_error = None
        except OSError as exc:
            self.last_save_error = str(exc)
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass

    # ---------- 关注列表 ----------

    @property
    def followings(self) -> list[dict]:
        return self.data["followings"].get("items", [])

    def followings_age_days(self) -> float:
        ts = self.data["followings"].get("refreshed_at")
        if not ts:
            return float("inf")
        try:
            then = datetime.strptime(ts, "%Y-%m-%d %H:%M")
        except ValueError:
            return float("inf")
        return (datetime.now() - then).total_seconds() / 86400

    def set_followings(self, items: list[dict], declared: int | None = None) -> None:
        self.data["followings"] = {
            "schema": 2,
            "refreshed_at": now_str(),
            "declared": declared,
            "items": items,
        }

    def followings_incomplete(self) -> bool:
        """缓存是否不可信。

        两种情况要重抓：
        - 老版本缓存（schema < 2，可能是只读了一页的残缺数据）；
        - 记录过页面声明总数，而缓存条数明显对不上。
        """
        f = self.data["followings"]
        if f.get("schema") != 2:
            return bool(f.get("items"))
        declared = f.get("declared")
        if declared and len(f.get("items", [])) < int(declared):
            return True
        return False

    # ---------- 单个 UP ----------

    def up(self, mid: str) -> dict:
        ups = self.data["ups"]
        if mid not in ups:
            ups[mid] = {
                "uname": "",
                "first_recorded": today_str(),
                "latest_pub": None,
                "seen": [],
                "history": [],
            }
        entry = ups[mid]
        entry.setdefault("seen", [])
        entry.setdefault("history", [])
        return entry

    def record_videos(self, mid: str, uname: str, videos: list[dict]) -> list[dict]:
        """把本轮抓到的视频并入历史，返回其中"首次出现"的视频列表。"""
        entry = self.up(mid)
        entry["uname"] = uname or entry.get("uname", "")
        seen = set(entry["seen"])
        fresh: list[dict] = []
        history = entry["history"]

        for v in videos:
            bv = v.get("bv")
            if not bv:
                continue
            if bv not in seen:
                seen.add(bv)
                item = {
                    "bv": bv,
                    "title": v.get("title", ""),
                    "pub": v.get("pub_date"),
                    "url": v.get("url", ""),
                    "first_seen": today_str(),
                }
                history.append(item)
                fresh.append(item)

        entry["seen"] = sorted(seen)
        if videos:
            dated = [v for v in videos if v.get("pub_date")]
            if dated:
                newest = max(dated, key=lambda v: v["pub_date"])
                entry["latest_pub"] = newest["pub_date"]
                entry["latest_title"] = newest.get("title", "")
                entry["latest_url"] = newest.get("url", "")
            else:
                head = videos[0]
                entry["latest_title"] = head.get("title", "")
                entry["latest_url"] = head.get("url", "")
        # 历史只留最近 60 条，防止文件无限膨胀
        entry["history"] = history[-60:]
        return fresh

    def recent_updates(self, mid: str, days: int = 30) -> int:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        entry = self.data["ups"].get(mid, {})
        return sum(1 for h in entry.get("history", []) if (h.get("pub") or "") >= cutoff)

    # ---------- 分区标注（zone） ----------

    def set_zone(self, mid: str, info: dict) -> None:
        """记录 UP 的分区信息：主分区 + 子分区 + 标注时间。"""
        entry = self.data["ups"].get(mid)
        if entry is None or not info or not info.get("zone"):
            return
        entry["zone"] = info["zone"]
        entry["zone_sub"] = info.get("sub") or ""
        entry["zone_at"] = now_str()

    # ---------- 收藏夹里出现的 UP（fav_ups） ----------
    #
    # 收藏夹的视频可能来自没关注的 UP，这些人不在 ups 里，也就没有分区标注。
    # 单独建一张缓存表存它们的 uname/分区，避免每次刷新收藏夹都重新查接口。

    def fav_up(self, mid: str) -> dict:
        return self.data.setdefault("fav_ups", {}).get(str(mid), {})

    def set_fav_up(self, mid: str, info: dict) -> None:
        if not info or not info.get("zone"):
            return
        self.data.setdefault("fav_ups", {})[str(mid)] = {
            "uname": info.get("uname", ""),
            "zone": info["zone"],
            "zone_sub": info.get("sub") or "",
            "at": now_str(),
        }

    # ---------- 断点续跑（current_run） ----------
    #
    # 背景：看门狗强杀进程（exit 9）后，一键运行.bat 会自动续跑，但每次
    # 都从第 1 个 UP 重新抓——如果某个 UP 的页面必然卡死，就会永远死在
    # 同一个地方。current_run 记录"这一批"的进度：
    #   done        —— 已成功处理完的 mid（续跑时直接跳过）
    #   in_progress —— 上次死在哪个 mid（续跑时重试它）
    #   stuck       —— 同一个 mid 连续卡死次数，>=2 就本轮跳过，下次整批再试

    RESUME_MAX_AGE_H = 24  # 超过 24 小时的断点视为过期，不续

    def begin_run(self) -> dict | None:
        """开始一轮。若存在 24 小时内的未完成断点，返回它供续跑，否则返回 None。"""
        prev = self.data.get("current_run")
        if prev:
            try:
                then = datetime.strptime(prev.get("started_at", ""), "%Y-%m-%d %H:%M:%S")
                age_h = (datetime.now() - then).total_seconds() / 3600
            except ValueError:
                age_h = float("inf")
            if age_h <= self.RESUME_MAX_AGE_H:
                self.data["current_run"] = {
                    "started_at": prev["started_at"],
                    "done": dict(prev.get("done", {})),
                    # 保留「上次死在哪个 UP」：续跑时只对它走认领，才能累计卡死次数
                    "in_progress": prev.get("in_progress"),
                    "stuck": dict(prev.get("stuck", {})),
                }
                return self.data["current_run"]
        self.data["current_run"] = {
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "done": {},
            "in_progress": None,
            "stuck": {},
        }
        return None

    def mark_in_progress(self, mid: str) -> bool:
        """标记"正在处理这个 UP"。若上次就是死在它身上，返回 True（重试计数 +1）。"""
        cur = self.data["current_run"]
        retry = cur.get("in_progress") == mid
        cur["in_progress"] = mid
        if retry:
            stuck = cur.setdefault("stuck", {})
            stuck[mid] = stuck.get(mid, 0) + 1
        return retry

    def mark_done(self, mid: str) -> None:
        """这个 UP 已成功写完（只改内存，落盘交给调用方统一的 state.save()）。"""
        cur = self.data["current_run"]
        cur["done"][mid] = 1
        if cur.get("in_progress") == mid:
            cur["in_progress"] = None

    def finish_run(self) -> None:
        """整批正常结束，清除断点（被看门狗强杀时不会走到这里，断点得以保留）。"""
        self.data.pop("current_run", None)

    # ---------- 运行记录 ----------

    def add_run(self, record: dict) -> None:
        record.setdefault("at", now_str())
        self.data["runs"].append(record)
        self.data["runs"] = self.data["runs"][-MAX_RUNS:]

# ════════════════════════════════════════════════════════════════════
# 06 / 20 · controls —— 运行中按 P 暂停、再按 P（或 R）继续
#    （原文件：bilisync/controls.py）
# ════════════════════════════════════════════════════════════════════

"""运行中的暂停控制：按 P 暂停，再按 P（或 R）继续抓取。

为什么需要：全量 200+ 个 UP 要跑半小时以上，中途可能想临时腾出手、
或者发现 B 站开始弹验证码想停一下再继续。暂停只发生在「一个 UP 处理完
之后」和「长等待之中」，不会打断正在进行的页面操作。

实现要点：
- Windows 用 msvcrt 非阻塞读键；其他平台退化为 select（终端需回车才响应）。
- 只在真正的控制台里生效（stdin 是 tty）；定时任务、管道、重定向自动禁用，
  避免把"读不到键"误判成暂停。
- 暂停期间持续喂看门狗，否则 180 秒无进展会被判成卡死强杀。
"""







_WINDOWS = platform.system() == "Windows"


def _stdin_is_interactive() -> bool:
    try:
        return sys.stdin is not None and sys.stdin.isatty()
    except Exception:
        return False


class PauseController:
    def __init__(self, enabled: bool = True):
        self.enabled = bool(enabled) and _stdin_is_interactive()
        self.paused = False
        self._disabled_reason = "" if self.enabled else "非交互环境，暂停键不可用"

    # ---------- 按键读取 ----------

    def _read_key(self) -> str:
        if _WINDOWS:
            try:
                import msvcrt

                if not msvcrt.kbhit():
                    return ""
                ch = msvcrt.getwch()
                if ch in ("\x00", "\xe0"):  # 方向键等双字节按键，丢弃后半段
                    msvcrt.getwch()
                    return ""
                return ch
            except Exception:
                return ""
        try:
            import select

            if select.select([sys.stdin], [], [], 0)[0]:
                return sys.stdin.read(1)
        except Exception:
            return ""
        return ""

    # ---------- 对外接口 ----------

    def check(self, log, heartbeat=None) -> None:
        """在一个安全点调用：处理暂停/继续。暂停时本函数会原地阻塞。"""
        if not self.enabled:
            return

        key = self._read_key()
        if key and key.lower() == "p":
            self.paused = not self.paused
            log("⏸ 已暂停" if self.paused else "▶ 已恢复")

        if not self.paused:
            return

        started = time.time()
        last_tick = started
        log("⏸ 暂停中：按 P 或 R 继续（当前 UP 处理完即停，不会丢数据）")
        while True:
            if heartbeat:
                heartbeat()
            time.sleep(0.2)
            pressed = self._read_key()
            if pressed and pressed.lower() in ("p", "r"):
                self.paused = False
                log(f"▶ 继续抓取（暂停了 {int(time.time() - started)} 秒）")
                return
            if time.time() - last_tick >= 20:
                last_tick = time.time()
                log(f"⏸ 仍在暂停，已暂停 {int(time.time() - started)} 秒…（P/R 继续）")

# ════════════════════════════════════════════════════════════════════
# 07 / 20 · watchdog —— 看门狗：超时无进展则落盘取证并强杀，由外层自动续跑
#    （原文件：bilisync/watchdog.py）
# ════════════════════════════════════════════════════════════════════

"""看门狗：防止某次页面操作把整个流程永久挂死。

背景：Playwright 的 page.evaluate 没有超时机制，页面渲染进程一旦假死
（B 站页面脚本很重，偶发），主线程会永远等在那里——用户看到的就是
"卡住不动、一个字都不输出"。看门狗线程每秒检查一次"距上次进展的秒数"，
超时先落盘取证、再强制退出（退出码 9），由 一键运行.bat 自动续跑。

v2 加固（2026-10-30，针对"卡在 73/246 静默死亡"）：
1. 诊断信息先写进 logs/watchdog.log —— 控制台可能被"快速编辑模式"的文本
   选中阻塞，print 会永远挂住；写文件不受影响，事后可取证。
2. 控制台横幅放到独立线程里打，主流程只等 2 秒就继续执行强杀 + 退出，
   无论控制台是否被阻塞都保证退出。
"""










DEFAULT_TIMEOUT = 180.0

# 日志目录：bili-watch/logs/
LOG_DIR = PROJECT_ROOT / "logs"


def file_log(lines: list[str]) -> None:
    """把诊断信息追加到 logs/watchdog.log（控制台不可靠时的取证通道）。"""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with (LOG_DIR / "watchdog.log").open("a", encoding="utf-8", errors="replace") as fh:
            fh.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n")
            for ln in lines:
                fh.write(ln + "\n")
    except Exception:
        pass  # 取证失败也不能阻止强制退出


class Watchdog:
    def __init__(self, timeout_s: float = DEFAULT_TIMEOUT):
        self.timeout_s = max(30.0, float(timeout_s))
        self._last = time.time()
        self._last_msg = "(尚未开始)"
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ---------- 主线程调用 ----------

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True, name="bili-watchdog")
        self._thread.start()

    def beat(self, msg: str = "") -> None:
        """报告"我还有进展"。每个日志行 / 每个长等待片段都应该 beat 一次。"""
        self._last = time.time()
        if msg:
            self._last_msg = msg

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    # ---------- 看门狗线程 ----------

    def _loop(self) -> None:
        while not self._stop.wait(timeout=1.0):
            idle = time.time() - self._last
            if idle <= self.timeout_s:
                continue
            idle = int(idle)
            banner = [
                "=" * 58,
                f"[watchdog] 已 {idle} 秒没有任何进展，判定流程卡死。",
                f"[watchdog] 卡住前的最后动作：{self._last_msg}",
                "[watchdog] 强制退出（exit code 9），外层脚本会从断点自动续跑。",
                "=" * 58,
            ]
            # 1) 先落盘取证（不依赖控制台是否可用）
            file_log(banner)
            # 2) 再尝试在控制台展示：放独立线程，即便 print 被阻塞也不影响退出
            threading.Thread(
                target=self._print_banner, args=(banner,), daemon=True, name="bili-watchdog-print"
            ).start()
            time.sleep(2.0)  # 给打印线程一点时间
            _kill_stale_browser_then_exit()

    @staticmethod
    def _print_banner(banner: list[str]) -> None:
        try:
            print("", flush=True)
            for ln in banner:
                print(ln, flush=True)
        except Exception:
            pass


def _kill_stale_browser_then_exit() -> None:
    """退出前把残留的 chromium（以我们的 .profile 为命令行特征）杀掉，
    否则强杀 python 后浏览器进程残留，下次启动会因 profile 锁失败。"""
    here = str(PROJECT_ROOT).lower()
    try:
        ps = (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.CommandLine -and $_.CommandLine.ToLower().Contains('" + here + "') "
            " -and $_.Name -match 'chrome' } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, timeout=30,
        )
    except Exception:
        pass
    os._exit(9)

# ════════════════════════════════════════════════════════════════════
# 08 / 20 · detect —— Obsidian 探测：装了没、有没有可用的库（仅用于日志与提示）
#    （原文件：bilisync/detect.py）
# ════════════════════════════════════════════════════════════════════

"""Obsidian 检测：确认本机是否装了 Obsidian、有没有可用的库，仅用于日志与提示。

判定条件（满足任一即视为「系统里装了 Obsidian」）：

  A. 配置文件里有真实存在的库 —— 最可信，同时能拿到库路径：
     - Windows：%APPDATA%\\obsidian\\obsidian.json
     - macOS  ：~/Library/Application Support/obsidian/obsidian.json
     - Linux  ：~/.config/obsidian/obsidian.json
     JSON 结构形如 {"vaults": {"<id>": {"path": "D:/Notes", "ts": 1690000000, "open": true}}}；
     逐个校验 path 是否真实存在，优先取 open=true 的，其次取 ts 最新的。
  B. 注册表痕迹（仅 Windows）：
     - HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Obsidian
     - HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Obsidian
     - HKCU\\Software\\Classes\\obsidian  （obsidian:// 协议处理程序）
  C. 安装目录里有可执行文件：
     - Windows：%LOCALAPPDATA%\\Obsidian\\Obsidian.exe、
                %LOCALAPPDATA%\\Programs\\Obsidian\\Obsidian.exe、
                %PROGRAMFILES%\\Obsidian\\Obsidian.exe 等
     - macOS  ：/Applications/Obsidian.app
     - Linux  ：PATH 里的 obsidian、/opt/Obsidian/obsidian
  D. config.toml 里显式配置的 vault.root 存在，且其下有 .obsidian 目录
     （等价于「这个目录确实是一个 Obsidian 库」，比只看配置文件更直接）

两条结论要分开看：
  installed=True  —— 装了 Obsidian（A/B/C/D 任一成立）
  usable=True     —— 找到了可写的库根目录（说明本机已经有一个现成的库）

检测结果只用于日志展示与「将要写入的库」提示，**不决定能不能写笔记**：
即使本机没装 Obsidian、库路径也不存在，也照样写 Markdown
（目标目录由 prepare_obsidian() 自动创建，父级目录全部补齐）。
"""













@dataclass
class ObsidianStatus:
    installed: bool = False
    vault_root: Path | None = None
    evidence: list[str] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        return bool(self.vault_root and self.vault_root.exists())

    def why_not_usable(self) -> str:
        if not self.installed:
            return "未检测到 Obsidian（配置文件 / 注册表 / 安装目录均无痕迹）"
        if not self.vault_root:
            return "检测到 Obsidian，但没有找到任何已创建的库（vault）"
        return f"检测到的库路径不可用：{self.vault_root}"


def _obsidian_json_paths() -> list[Path]:
    """各平台 Obsidian 全局配置（记录所有库）的候选位置。"""
    system = platform.system()
    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        return [Path(appdata) / "obsidian" / "obsidian.json"] if appdata else []
    if system == "Darwin":
        return [Path.home() / "Library" / "Application Support" / "obsidian" / "obsidian.json"]
    return [Path.home() / ".config" / "obsidian" / "obsidian.json"]


def _exe_candidates() -> list[Path]:
    system = platform.system()
    if system == "Windows":
        env = os.environ
        bases = [
            (env.get("LOCALAPPDATA"), "Obsidian", "Obsidian.exe"),
            (env.get("LOCALAPPDATA"), "Programs", "Obsidian", "Obsidian.exe"),
            (env.get("PROGRAMFILES"), "Obsidian", "Obsidian.exe"),
            (env.get("PROGRAMFILES(X86)"), "Obsidian", "Obsidian.exe"),
        ]
        return [Path(b, *rest) for b, *rest in bases if b]
    if system == "Darwin":
        return [Path("/Applications/Obsidian.app")]
    return [Path("/usr/bin/obsidian"), Path("/opt/Obsidian/obsidian")]


def _registry_hits(evidence: list[str]) -> bool:
    """Windows 注册表痕迹：卸载项或 obsidian:// 协议处理程序。"""
    if platform.system() != "Windows":
        return False
    try:
        import winreg  # type: ignore[import-not-found]
    except ImportError:
        return False

    keys = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Obsidian"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Obsidian"),
        (winreg.HKEY_CURRENT_USER, r"Software\Classes\obsidian"),
    ]
    hit = False
    for hive, path in keys:
        try:
            with winreg.OpenKey(hive, path):
                evidence.append(f"注册表存在 Obsidian 痕迹：{path.split(chr(92))[-1]}")
                hit = True
        except OSError:
            continue
    return hit


def _vaults_from_json(path: Path, evidence: list[str]) -> Path | None:
    """从 obsidian.json 里挑一个真实存在的库：优先 open=true，其次 ts 最新。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        evidence.append(f"配置文件读取失败（{path}）：{exc}")
        return None

    vaults = data.get("vaults") or {}
    if not isinstance(vaults, dict) or not vaults:
        evidence.append(f"配置文件里没有任何库记录：{path}")
        return None

    entries = sorted(
        (v for v in vaults.values() if isinstance(v, dict)),
        key=lambda v: (1 if v.get("open") else 0, v.get("ts") or 0),
        reverse=True,
    )
    missing = []
    for v in entries:
        raw = v.get("path") or ""
        if not raw:
            continue
        p = Path(raw)
        if p.exists():
            evidence.append(f"配置文件记录的库存在：{p}")
            return p
        missing.append(str(p))
    if missing:
        evidence.append(f"配置文件记录的库路径都已被移动或删除：{missing[0]}")
    return None


def detect_obsidian(cfg: Config) -> ObsidianStatus:
    st = ObsidianStatus()

    # A. 全局配置文件里的库（最可信的证据）
    for conf in _obsidian_json_paths():
        if not conf.exists():
            continue
        st.evidence.append(f"找到 Obsidian 配置文件：{conf}")
        st.installed = True
        if st.vault_root is None:
            st.vault_root = _vaults_from_json(conf, st.evidence)

    # B. 注册表痕迹（仅 Windows，说明装了但不一定有库）
    if _registry_hits(st.evidence):
        st.installed = True

    # C. 安装目录里的可执行文件
    for exe in _exe_candidates():
        if exe.exists():
            st.evidence.append(f"找到 Obsidian 程序：{exe}")
            st.installed = True
            break
    if platform.system() == "Linux" and shutil.which("obsidian"):
        st.evidence.append("PATH 中存在 obsidian 命令")
        st.installed = True

    # D. config.toml 指定的库路径（最快，也最贴合本机实际）
    root = cfg.vault.root
    if root.exists() and (root / ".obsidian").is_dir():
        st.evidence.append(f"config.toml 配置的库根目录有效（含 .obsidian）：{root}")
        st.installed = True
        if st.vault_root is None:
            st.vault_root = root

    if not st.evidence:
        st.evidence.append("未发现任何 Obsidian 痕迹（配置文件 / 注册表 / 安装目录 / 库路径）")
    return st

# ════════════════════════════════════════════════════════════════════
# 09 / 20 · output —— 输出落盘层：目录整条创建、原子写入、失败说人话
#    （原文件：bilisync/output.py）
# ════════════════════════════════════════════════════════════════════

"""输出落盘层：目录准备、原子写入、失败提示。

为什么单独抽出这一层：

1. **不依赖 Obsidian** —— 笔记就是普通 Markdown 文件，写进任何可写目录都成立。
   装没装 Obsidian、有没有建过库，都不应该影响文件能不能生成。
2. **目录缺失就整条建出来** —— 库根 / 分区目录 / UP 子文件夹 / 附件目录
   一次性 mkdir(parents=True)，父级有几层建几层。
3. **失败要说人话** —— 不把 WinError 5/32/112 直接甩给用户，
   而是给出「哪个路径 + 为什么 + 怎么办」。
4. **写完再验一次** —— 落盘后确认文件真的存在且非空，
   避免杀毒软件拦截、只读盘映射这类「静默失败」。

模式与格式互不干扰：本模块只管「把内容写到某个目录」，不关心内容长什么样。
本程序只产出 Obsidian Markdown（UP 笔记 / 分区笔记 / 总览页 / 收藏夹），
不生成任何 Word 文档。
"""








# Windows 常见错误码 → 人话。Linux/macOS 走 errno 的小号值，一并覆盖。
_HINTS: dict[int, str] = {
    2: "找不到目标路径（盘符或目录已被移除）",
    3: "目标路径不存在（U 盘 / 网络盘可能已断开）",
    5: "拒绝访问（目录只读、归属其他账户，或被安全软件拦截）",
    13: "没有权限读写该目录",
    21: "目标是目录，不是文件",
    28: "磁盘空间不足",
    32: "文件正被其他程序占用（Obsidian 可能正开着它）",
    36: "文件名过长",
    112: "磁盘空间不足",
    123: "文件名或路径包含非法字符",
    183: "同名文件已存在（可能挡住了目录创建）",
    206: "路径过长（Windows 默认上限 260 字符，把库移到更浅的目录）",
    267: "目录名无效",
}


class OutputError(RuntimeError):
    """输出阶段的失败。消息里已包含路径、原因和下一步建议，可直接展示给用户。"""


def describe(exc: BaseException) -> str:
    """把 OSError 翻译成「原因 + 建议」，认不出的错误码就原样带上。"""
    code = getattr(exc, "winerror", None) or getattr(exc, "errno", None)
    hint = _HINTS.get(code) if isinstance(code, int) else None
    raw = getattr(exc, "strerror", "") or str(exc)
    if hint:
        return f"{hint}（{raw}）" if raw and raw != hint else hint
    return raw or exc.__class__.__name__


def ensure_dir(path: Path | str, what: str = "目录") -> Path:
    """确保目录存在（父级一并创建）；建不出来就抛带路径的 OutputError。"""
    p = Path(path)
    if p.is_dir():
        return p
    if p.exists():
        raise OutputError(
            f"无法创建{what}：{p}\n"
            f"  原因：同名文件已存在，挡住了目录\n"
            f"  建议：把该文件改名或删除，或在 config.toml 里换一个目录。"
        )
    # 盘符不存在 / 别人机器的用户目录：mkdir 只会返回一个含糊的 WinError，这里先说清楚
    reason = _unreachable_reason(p)
    if reason:
        raise OutputError(
            f"无法创建{what}：{p}\n"
            f"  原因：{reason}\n"
            f"  建议：确认该路径所在的磁盘存在且可写，或修改 config.toml 里对应的路径。"
        )
    # 上级路径被文件挡住时，mkdir 只会丢一句 WinError 183，这里提前说清楚是哪一层
    probe = p.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    if probe.exists() and not probe.is_dir():
        raise OutputError(
            f"无法创建{what}：{p}\n"
            f"  原因：上级路径 {probe} 是一个文件，挡住了目录创建\n"
            f"  建议：把 {probe} 改名或删除，或在 config.toml 里换一个目录。"
        )
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OutputError(
            f"无法创建{what}：{p}\n"
            f"  原因：{describe(exc)}\n"
            f"  建议：确认该路径所在的磁盘存在且可写；路径过长请换到更浅的目录，"
            f"或修改 config.toml 里对应的路径。"
        ) from exc
    if not p.is_dir():
        raise OutputError(f"无法创建{what}：{p}（创建后仍不可用）")
    return p


def write_text(path: Path | str, content: str, what: str = "文件") -> Path:
    """原子写入文本：临时文件 → 替换，最后校验文件确实存在且非空。"""
    p = Path(path)
    ensure_dir(p.parent, f"{what}所在目录")
    tmp = p.with_name(p.name + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, p)
    except OSError as exc:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise OutputError(
            f"{what}写入失败：{p}\n"
            f"  原因：{describe(exc)}\n"
            f"  建议：关闭可能正在打开该文件的程序后重试。"
        ) from exc
    return _verify(p, what)


def _verify(p: Path, what: str) -> Path:
    """落盘后复核：文件不在或为空，都当成失败，绝不静默。"""
    try:
        size = p.stat().st_size
    except OSError as exc:
        raise OutputError(
            f"{what}写入后校验失败：{p}\n"
            f"  原因：{describe(exc)}"
        ) from exc
    if size <= 0:
        raise OutputError(
            f"{what}写入后校验失败：{p}\n"
            f"  原因：文件为空（可能被安全软件拦截，或磁盘只读）\n"
            f"  建议：把输出目录换到非系统盘后重试。"
        )
    return p


def _writable_probe(directory: Path) -> None:
    """在目录里试写一个临时文件再删掉 —— 比只看权限位可靠。"""
    probe = directory / ".bilisync_write_test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        raise OutputError(
            f"目录不可写：{directory}\n"
            f"  原因：{describe(exc)}\n"
            f"  建议：换一个有写权限的目录，或以管理员身份运行。"
        ) from exc


def _unreachable_reason(path: Path) -> str | None:
    """判断一个路径在当前机器上是否根本不可能创建；能建就返回 None。

    两种「换机器就会踩」的情况：
      1. 盘符 / 挂载点不存在（配置里写着 F:\\、Z:\\ 这类）；
      2. 路径指向别人机器的用户目录（C:\\Users\\wu\\... 而本机没有 wu 这个用户）。
    只做判定、不创建任何东西 —— 避免在 C:\\Users\\ 下凭空造出一个陌生用户名目录。
    """
    anchor = Path(path.anchor) if path.anchor else None
    if not anchor or not anchor.exists():
        return f"所在磁盘 / 挂载点不存在：{path.anchor or path}"
    parts = path.parts
    for i, seg in enumerate(parts):
        if seg.lower() in ("users", "home") and i + 2 < len(parts):
            user_dir = Path(*parts[: i + 2])
            if not user_dir.exists():
                return f"路径属于其他机器的用户目录（本机没有 {user_dir}）"
    return None


def _reachable(path: Path) -> bool:
    return _unreachable_reason(path) is None


def default_notes_root() -> Path:
    """没有任何可用配置时的兜底笔记目录（本机文档目录，一定存在父级）。"""
    return Path.home() / "Documents" / "B站关注更新" / "Obsidian库"


def ensure_vault_marker(root: Path) -> None:
    """给新建的笔记根目录补一个最小 .obsidian，日后用 Obsidian 打开就是合法库。

    只在「目录里还没有 .obsidian」时补，且失败不影响主流程（笔记照样写入）。
    """
    marker = root / ".obsidian"
    if marker.is_dir():
        return
    try:
        marker.mkdir(parents=True, exist_ok=True)
        app = marker / "app.json"
        if not app.exists():
            app.write_text("{}\n", encoding="utf-8")
    except OSError:
        pass


def retarget_vault(cfg: Config, notes_root: Path) -> None:
    """把 vault 的各项路径重新挂到新的笔记根目录下（保持原有目录层级）。"""
    v = cfg.vault
    assets_name = v.covers_dir.parent.name or "_assets"
    up_name = v.up_dir.name or "08_B站关注"
    index_name = v.index_note.name or "B站关注总览.md"

    v.root = notes_root
    v.notes_root = notes_root
    v.up_dir = notes_root / up_name
    v.ups_dir = v.up_dir / v.ups_subdir
    v.covers_dir = v.up_dir / assets_name / "covers"
    v.avatars_dir = v.up_dir / assets_name / "avatars"
    v.index_note = v.up_dir / index_name


def _brief(exc: BaseException) -> str:
    """从多行错误里抽出「原因」那一句，用于一行日志。"""
    for line in str(exc).splitlines():
        s = line.strip()
        if s.startswith("原因："):
            return s[3:].strip()
    return str(exc).splitlines()[0].strip() if str(exc).strip() else exc.__class__.__name__


def prepare_obsidian(cfg: Config, *, log=None) -> Path:
    """准备 Obsidian 笔记的全部目录，返回实际使用的笔记根目录。

    顺序：
      1. config.toml 里的 notes_root —— 能用就用（不存在就整条建出来）；
      2. 它的盘符/挂载点不存在（例如配置还是别人机器上的 F:\\）→ 换成本机兜底目录；
      3. 兜底目录也建不出来 → 抛 OutputError。
    """
    v = cfg.vault
    fallback = default_notes_root()
    candidates = [v.notes_root]
    if fallback != v.notes_root:
        candidates.append(fallback)

    errors: list[str] = []
    for cand in candidates:
        reason = _unreachable_reason(cand)
        if reason:
            errors.append(f"{cand}\n  原因：{reason}")
            if log:
                log(f"[warn] 笔记目录不可用（{reason}），改试下一个：{cand}")
            continue
        try:
            ensure_dir(cand, "Obsidian 笔记根目录")
            ensure_dir(cand / (v.up_dir.name or "08_B站关注"), "B站分区目录")
            retarget_vault(cfg, cand)
            ensure_dir(cfg.vault.ups_dir, "UP 笔记目录")
            ensure_dir(cfg.vault.covers_dir, "封面附件目录")
            ensure_dir(cfg.vault.avatars_dir, "头像附件目录")
            ensure_vault_marker(cfg.vault.root)
            _writable_probe(cfg.vault.ups_dir)
        except OutputError as exc:
            errors.append(str(exc))
            if log:
                log(f"[warn] 笔记目录不可用（{_brief(exc)}），改试下一个：{cand}")
            continue
        if log:
            log(f"✓ 笔记目录已就绪：{cand}")
        return cand

    detail = "\n".join(f"  - {e}" for e in errors) or "  - 无可用候选目录"
    raise OutputError(
        "无法准备 Obsidian 笔记目录（已尝试以下位置）：\n"
        f"{detail}\n"
        "  建议：在 config.toml 的 [vault] 里把 notes_root 改成本机可写的目录，"
        "例如 C:/Users/<你的用户名>/Documents/B站关注更新/Obsidian库。"
    )


def plan_obsidian(cfg: Config) -> tuple[Path, str]:
    """不创建任何目录，只按 prepare_obsidian 同样的规则算出「实际会用哪个笔记根」。

    给 doctor 用：自检要预测运行时落在哪，而不是照着配置里那条失效路径报错。
    返回（笔记根目录, 可写性说明）。
    """
    v = cfg.vault
    fallback = default_notes_root()
    candidates = [v.notes_root] + ([fallback] if fallback != v.notes_root else [])
    reasons: list[str] = []
    for cand in candidates:
        reason = _unreachable_reason(cand)
        if reason is None:
            ok, detail = check_dir(cand)
            if ok:
                return cand, detail
            reason = detail
        reasons.append(f"{cand}：{reason}")
    raise OutputError(
        "没有可用的笔记根目录：\n" + "\n".join(f"  - {t}" for t in reasons)
    )


def check_dir(path: Path | str) -> tuple[bool, str]:
    """只检查不创建：给 doctor 用。返回（是否可写, 说明）。"""
    p = Path(path)
    reason = _unreachable_reason(p)
    if reason:
        return False, f"{reason}：{p}"
    probe = p
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    if probe.exists() and not probe.is_dir():
        return False, f"{probe} 是文件，不是目录"
    try:
        _writable_probe(probe)
    except OutputError as exc:
        return False, str(exc).replace("\n", " ")
    return True, f"可写（最近的可写目录：{probe}）"

# ════════════════════════════════════════════════════════════════════
# 10 / 20 · notes —— Obsidian 笔记渲染：UP 笔记 / 分区笔记 / 总览页，手工区原样保留
#    （原文件：bilisync/notes.py）
# ════════════════════════════════════════════════════════════════════

"""Obsidian 笔记渲染。

三个硬约束：
1. 「我的笔记」区块必须原样保留 —— 重写整篇笔记时只替换生成区，手工区逐字回填。
2. 文件名要能容错 —— UP 名里可能出现 / : ? 等非法字符，同名不同 UP 要能区分。
3. 图片引用只写文件名（`![[BVxxxx.jpg|380]]`）—— 封面按 BV 号、头像按 mid 命名，全库唯一。
   不写 `_assets/covers/...` 这种多级路径，是因为笔记挪进子文件夹后相对位置会变，
   而 Obsidian 对「唯一的裸文件名」永远能解析到，不受笔记所在层级影响。

目录层级：`B站UP文件夹/` 下先按分区分子文件夹，再放 UP 笔记::

    08_B站关注/
    ├── B站关注总览.md          ← 入口：分区导航（链到分区笔记）+ 运行历史
    ├── 收藏夹.md
    ├── B站UP文件夹/
    │   ├── 科技.md             ← 分区笔记：只收录该分区的 UP（双链按分区隔离）
    │   ├── 科技/
    │   │   ├── 米奇沃克斯.md
    │   │   └── 影视飓风.md
    │   └── 未分区/
    └── _assets/{covers,avatars}

因此双链必须带上级目录：`[[B站UP文件夹/科技/米奇沃克斯|米奇沃克斯]]`。
只写 `[[B站UP文件夹/米奇沃克斯]]` 会解析失败（Obsidian 按路径后缀匹配）。

双链分工：总览页只链 15 个分区笔记（不直接链 UP），UP 双链只出现在
各分区笔记里 —— 这样 UP 笔记的「反向链接/关系图谱」按分区隔离，
不会全部挂在总览一张大表上。
"""










ILLEGAL = re.compile(r'[\\/:*?"<>|#^\[\]\x00-\x1f]')
MANUAL_BEGIN = "<!-- manual:begin -->"
MANUAL_END = "<!-- manual:end -->"
MANUAL_PLACEHOLDER = "<!-- 这一块归你，脚本不会覆盖；删掉上下两行标记才会重置 -->"
MANUAL_HEADING = "## 我的笔记"

# 分区未知的笔记统一放这个文件夹（读起来比 `_未标注` 自然，也不会被当成 UP 名）
ZONE_UNKNOWN = UNZONED


def zone_dir(zone: str | None) -> str:
    """分区名 → 子文件夹名。空分区归入「未分区」。"""
    name = ILLEGAL.sub("_", (zone or "").strip()).strip(" .")
    return name or ZONE_UNKNOWN


def note_relpath(ups_subdir: str, zone: str | None, note_name: str) -> str:
    """笔记在库内的相对路径（不带 .md），用于双链：`B站UP文件夹/科技/某UP`。"""
    return f"{ups_subdir}/{zone_dir(zone)}/{note_name}"


def note_path(ups_dir: Path, zone: str | None, note_name: str) -> Path:
    """笔记的绝对落点：`B站UP文件夹/<分区>/<名字>.md`。"""
    return ups_dir / zone_dir(zone) / f"{note_name}.md"


def zone_note_relpath(ups_subdir: str, zone: str | None) -> str:
    """分区笔记的库内相对路径（不带 .md）：`B站UP文件夹/科技`。"""
    return f"{ups_subdir}/{zone_dir(zone)}"


def zone_note_path(ups_dir: Path, zone: str | None) -> Path:
    """分区笔记的绝对落点：`B站UP文件夹/<分区>.md`（与分区文件夹同名并排）。"""
    return ups_dir / f"{zone_dir(zone)}.md"


def is_zone_note(path: Path) -> bool:
    """靠 frontmatter 的 type 认分区笔记，避免把同名 UP 笔记误伤。"""
    head = read_note(path)[:300]
    return "type: bilibili-zone" in head


def find_note(ups_dir: Path, note_name: str) -> Path | None:
    """按文件名找笔记：先看分区子文件夹，再退到旧的扁平位置（迁移前行）。

    扁平位置上放的是分区笔记（`科技.md` 这类），UP 恰好与分区同名时
    也要跳过它们、只认真正的 UP 笔记。
    """
    direct = ups_dir / f"{note_name}.md"
    if direct.exists() and not is_zone_note(direct):
        return direct
    if ups_dir.exists():
        hits = [h for h in sorted(ups_dir.rglob(f"{note_name}.md")) if not is_zone_note(h)]
        if hits:
            return hits[0]
    return None



def safe_filename(name: str, mid: str = "", taken: dict[str, str] | None = None) -> str:
    """把 UP 名转成合法文件名；同名但不同 mid 时追加 mid 后缀。"""
    base = ILLEGAL.sub("_", (name or f"UP_{mid}")).strip().strip(".")
    base = re.sub(r"\s+", " ", base)[:80] or f"UP_{mid}"
    if taken and mid:
        owner = taken.get(base.lower())
        if owner and owner != mid:
            base = f"{base} ({mid})"
    return base


def days_since(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (date.today() - d).days


def human_age(date_str: str | None) -> str:
    n = days_since(date_str)
    if n is None:
        return "未知"
    if n <= 0:
        return "今天"
    if n == 1:
        return "1 天前"
    return f"{n} 天前"


def yaml_str(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def read_note(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except OSError:
        return ""


def extract_manual(text: str) -> str:
    """取出用户手写区内容；标记丢了就退回「我的笔记」标题之后的部分。"""
    if not text:
        return ""
    m = re.search(re.escape(MANUAL_BEGIN) + r"(.*?)" + re.escape(MANUAL_END), text, re.S)
    if m:
        return m.group(1).strip("\n")
    idx = text.find(MANUAL_HEADING)
    if idx >= 0:
        return text[idx + len(MANUAL_HEADING):].strip("\n")
    return ""


def write_atomic(path: Path, content: str) -> None:
    """原子写入：目录缺失自动补齐父级，写失败抛带路径与原因的 OutputError。"""
    write_text(path, content, what="笔记")


def _cover_embed(cover_name: str | None, alt: str) -> str:
    if cover_name:
        return f"![[{cover_name}|380]]"
    return f"*(未取到封面：{alt})*"


def render_up_note(
    *,
    mid: str,
    uname: str,
    videos: list[dict],
    entry: dict,
    manual: str,
    cover_name_by_bv: dict[str, str],
    avatar_name: str | None,
    fresh_bvs: set[str],
    updates_30d: int,
    zone_info: dict | None = None,
) -> str:
    latest_pub = entry.get("latest_pub")
    zone_info = zone_info or {}
    zone_main = zone_info.get("zone") or entry.get("zone") or ""
    zone_sub = zone_info.get("sub") or entry.get("zone_sub") or ""
    yaml_lines = [
        "---",
        "type: bilibili-up",
        f"up: {yaml_str(uname)}",
        f"mid: {yaml_str(mid)}",
    ]
    if zone_main:
        yaml_lines.append(f"zone: {yaml_str(zone_main)}")
        if zone_sub:
            yaml_lines.append(f"zone_sub: {yaml_str(zone_sub)}")
    yaml_lines += [
        "tags:",
        "  - bilibili",
        "  - bilibili/up",
    ]
    if zone_main:
        # Obsidian 嵌套标签，可直接按分区检索/聚合
        yaml_lines.append(f"  - bilibili/zone/{zone_main}")
    yaml_lines += [
        f"updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"latest_pub: {latest_pub or ''}",
        f"videos_tracked: {len(videos)}",
        f"updates_30d: {updates_30d}",
        "---",
        "",
        f"# {uname}",
        "",
    ]
    lines = yaml_lines
    if avatar_name:
        lines += [f"![[{avatar_name}|72]]", ""]

    lines += [
        f"- **主页**：https://space.bilibili.com/{mid}",
    ]
    if zone_main:
        # 分区信息放在笔记最前：Obsidian 悬停双链预览时第一屏可见
        lines += [f"- **主分区**：{describe_zone({'zone': zone_main, 'sub': zone_sub})}"]
    lines += [
        f"- **最近更新**：{latest_pub or '未知'}（{human_age(latest_pub)}）",
        f"- **本次新增**：{len(fresh_bvs)} 条",
        f"- **首次记录**：{entry.get('first_recorded', '')}",
        "",
        "## 最新视频",
        "",
    ]

    if not videos:
        lines += ["> 没抓到视频。可能是网络/风控拦截，也可能是这个 UP 确实没有投稿。", ""]

    for i, v in enumerate(videos, 1):
        title = v.get("title") or "(无标题)"
        bv = v.get("bv", "")
        url = v.get("url") or (f"https://www.bilibili.com/video/{bv}" if bv else "")
        flag = " 🆕" if bv in fresh_bvs else ""
        meta = " · ".join(
            x for x in [
                f"`{v.get('pub_date') or v.get('pub_text') or '时间未知'}`",
                f"`{v.get('duration')}`" if v.get("duration") else "",
                f"[打开视频]({url})" if url else "",
            ] if x
        )
        lines += [
            f"### {i}. {title}{flag}",
            "",
            _cover_embed(cover_name_by_bv.get(bv), title),
            "",
            meta,
            "",
        ]

    # ---- 总结 ----
    total = len(videos)
    if latest_pub:
        first_seen = entry.get("first_recorded") or latest_pub
        summary = [
            f"- 当前跟踪 **{total}** 条最新投稿，最近一条发布于 **{latest_pub}**（{human_age(latest_pub)}）。",
            f"- 近 30 天共记录 **{updates_30d}** 条更新。",
            f"- 自 {first_seen} 起持续监控，累计见过 {len(entry.get('seen', []))} 条投稿。",
        ]
        age = days_since(latest_pub)
        if age is not None and age >= 30:
            summary.append(f"- ⚠️ 已 {age} 天没有更新，可能停更或改名。")
        elif age is not None and age <= 7:
            summary.append("- 更新频繁，属于活跃 UP。")
    else:
        summary = ["- 暂无可统计的数据。"]

    lines += ["## 总结", "", *summary, "", MANUAL_HEADING, MANUAL_BEGIN]
    if manual:
        lines += ["", manual]
    else:
        lines += ["", MANUAL_PLACEHOLDER]
    lines += ["", MANUAL_END, ""]
    return "\n".join(lines)


def _clean_mode(text: str) -> str:
    """老版本会在方式后面缀「（Obsidian 笔记 + Word 文档）」，现已只出 Markdown，去掉括注。"""
    t = re.sub(r"（[^）]*Word[^）]*）", "", text or "").strip()
    return t or "常规"


def render_index(
    *,
    rows: list[dict],
    last_run: dict | None,
    runs: list[dict] | None = None,
    stale_days: int = 30,
    ups_subdir: str = "B站UP文件夹",
    assets_subdir: str = "_assets",
    favs_note: str | None = None,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    def link(r: dict) -> str:
        """指向 UP 笔记的链接：必须带「分区」这一层，否则 Obsidian 解析不到。"""
        return f"[[{note_relpath(ups_subdir, r.get('zone'), r['note_name'])}\\|{r['uname']}]]"

    # 运行历史：全部历史记录（state.runs 持续累积，最近 30 次），最新在前。
    # 传入了 runs 就用完整历史；没传则退回只显示本次（老调用方兼容）。
    history = list(reversed(runs)) if runs is not None else ([last_run] if last_run else [])

    # 按分区聚合（官方分区顺序，未分区垫底），分区内保持传入的排序（最近更新在前）
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r.get("zone") or ZONE_UNKNOWN, []).append(r)
    zone_order = sort_zones(groups.keys())

    lines = [
        "---",
        "type: bilibili-index",
        "tags:",
        "  - bilibili",
        "  - bilibili/index",
        f"updated: {now}",
        f"ups: {len(rows)}",
        f"zones: {len(zone_order)}",
        "---",
        "",
        "# B站关注总览",
        "",
        "> 由 `bili-watch` 自动生成。目录层级：本页（入口）→ 分区 → UP 笔记。"
        "运行历史会持续累积（保留最近 30 次记录），每次运行只重写本页的数据区，不会删除历史。",
        "",
        f"目录结构：本页（入口）· `{ups_subdir}/<分区>.md`（分区笔记，收录该区全部 UP）"
        f" · `{ups_subdir}/<分区>/`（UP 笔记）· `{assets_subdir}/`（封面等附件）"
        + (f" · [[{favs_note}]]（我的 B 站收藏视频）" if favs_note else "")
        + "。",
        "",
    ]

    if last_run:
        errs = last_run.get("errors") or []
        lines += [
            "## 上次运行",
            "",
            f"- 时间：{last_run.get('at', '')}",
            f"- 方式：{_clean_mode(last_run.get('mode', ''))}",
            f"- 结果：扫描 {last_run.get('ups', 0)} 个 UP / 新增 {last_run.get('new', 0)} 条 / 失败 {len(errs)} 个",
            f"- 耗时：{last_run.get('duration', '')}",
        ]
        if errs:
            lines += ["", "**失败明细**：", ""]
            lines += [f"- `{e.get('uname') or e.get('mid')}`：{e.get('error')}" for e in errs[:10]]
        lines += [""]

    if history:
        lines += [
            "## 运行历史",
            "",
            "每次运行的累积记录（新 → 旧），不会被后续运行覆盖删除：",
            "",
            "| 时间 | 方式 | 扫描 UP | 新增 | 失败 | 耗时 |",
            "|---|---|--:|--:|--:|---|",
        ]
        for run in history:
            errs = run.get("errors") or []
            lines.append(
                f"| {run.get('at', '')} | {_clean_mode(run.get('mode', ''))} "
                f"| {run.get('ups', 0)} | {run.get('new', 0)} | {len(errs)} "
                f"| {run.get('duration', '')} |"
            )
        lines += [""]

    # ---- 分区导航：分区分组 + 每个分区直接列出 UP 名字（双链） ----
    # UP 名列在这里方便总览页一眼看到「哪个分区有谁」；
    # 详细表格仍在各分区笔记里（render_zone_note），双链关系两边都有。
    if zone_order:
        lines += [
            "## 分区导航",
            "",
            "每个分区一篇笔记（与本分区文件夹同名并排），里面是该分区的全部 UP：",
            "",
            "| 分区 | UP 数 | UP | 最近更新 | 分区笔记 | 文件夹 |",
            "|---|--:|---|---|---|---|",
        ]
        for z in zone_order:
            items = groups[z]
            newest = max((r.get("latest_pub") or "" for r in items), default="")
            zrel = zone_note_relpath(ups_subdir, z)
            ups_links = "、".join(link(r) for r in items)
            lines.append(
                f"| [[{zrel}\\|{z}]] | {len(items)} | {ups_links} | {newest or '—'} "
                f"| `[[{zrel}\\|打开]]` | `{zrel}/` |"
            )
        lines += [""]

    # ---- 按分区浏览的 UP 表已移到各分区笔记（见 render_zone_note）----
    # 总览页不再直接链 245 个 UP，反向链接/图谱按分区隔离。

    stale = [r for r in rows if (days_since(r.get("latest_pub")) or 0) >= stale_days]
    if stale:
        lines += [f"## 超过 {stale_days} 天未更新", ""]
        # 只链分区笔记不链 UP：保持「总览 → 分区 → UP」的链接方向，反向链接才干净
        lines += [
            f"{i}. [[{zone_note_relpath(ups_subdir, r.get('zone'))}|{zone_dir(r.get('zone'))}]] 的 "
            f"{r.get('uname')} —— {r.get('latest_pub') or '未知'}（{human_age(r.get('latest_pub'))}）"
            for i, r in enumerate(stale, 1)
        ]

    lines += ["", f"*最后更新：{now}*", ""]
    return "\n".join(lines)


def render_zone_note(
    zone: str,
    rows: list[dict],
    *,
    ups_subdir: str = "B站UP文件夹",
    index_name: str = "B站关注总览",
    manual: str = "",
) -> str:
    """渲染一个分区的「分区笔记」：`B站UP文件夹/<分区>.md`。

    分区笔记是 UP 双链的唯一来源 —— 每个 UP 的反向链接/图谱关系只挂在
    它所属的分区页上，而不是总览一张大表，双链面板因此按分区隔离。
    本身也带 frontmatter（type: bilibili-zone + 嵌套标签），可按分区检索。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    zdir = zone_dir(zone)
    newest = max((r.get("latest_pub") or "" for r in rows), default="")
    lines = [
        "---",
        "type: bilibili-zone",
        f"zone: {yaml_str(zdir)}",
        "tags:",
        "  - bilibili",
        f"  - bilibili/zone/{zdir}",
        f"updated: {now}",
        f"ups: {len(rows)}",
        "---",
        "",
        f"# {zdir}",
        "",
        f"> 「{zdir}」分区的 **{len(rows)}** 个 UP，最近更新 {newest or '—'}。"
        f"本页由 `bili-watch` 自动生成，双链只指向本分区的 UP；"
        f"全部分区入口见 [[{index_name}]]。",
        "",
        "| # | UP | 最近更新 | 距今 | 近 30 天 | 最新视频 |",
        "|--:|---|---|--:|--:|---|",
    ]
    for i, r in enumerate(rows, 1):
        age = days_since(r.get("latest_pub"))
        age_txt = f"{age} 天" if age is not None else "—"
        title = (r.get("latest_title") or "").replace("|", "\\|")
        if len(title) > 42:
            title = title[:42] + "…"
        video = f"[{title}]({r['latest_url']})" if r.get("latest_url") else title
        mark = " 🔥" if age is not None and age <= 2 else ""
        ref = f"[[{note_relpath(ups_subdir, r.get('zone'), r['note_name'])}\\|{r['uname']}]]"
        lines.append(
            f"| {i} | {ref}{mark} | {r.get('latest_pub') or '—'} | {age_txt} "
            f"| {r.get('updates_30d', 0)} | {video} |"
        )

    lines += ["", MANUAL_HEADING, MANUAL_BEGIN]
    lines += ["", manual] if manual else ["", MANUAL_PLACEHOLDER]
    lines += ["", MANUAL_END, ""]
    return "\n".join(lines)


def patch_zone(note_path: Path, zone_info: dict) -> bool:
    """给已有 UP 笔记原位补分区（不整篇重写，手写区与视频区原样保留）。

    幂等：重复执行不会再改动（值相同就直接返回 False）。三处改动：
      1. YAML 加/改 `zone: "主分区"` 与 `zone_sub: "子分区"`（插在 mid: 行后）；
      2. tags 加 `bilibili/zone/主分区`（Obsidian 嵌套标签，可按分区检索）；
      3. 正文「主页」行后加/改「主分区」描述行。
    """
    text = read_note(note_path)
    if not text or not zone_info.get("zone"):
        return False
    main = zone_info["zone"]
    sub = zone_info.get("sub") or ""
    desc = describe_zone(zone_info)
    changed = False

    # ---- YAML frontmatter ----
    m = re.match(r"^(---\n.*?\n---\n)", text, re.S)
    new_fm: str | None = None
    body = text
    if m:
        fm, body = m.group(1), text[m.end():]
        new_fm = fm
        if re.search(r"^zone: ", new_fm, re.M):
            new_fm = re.sub(r"^zone: .*$", f"zone: {yaml_str(main)}", new_fm, flags=re.M)
        else:
            new_fm = re.sub(r"^(mid: .*)$", lambda mm: f"{mm.group(1)}\nzone: {yaml_str(main)}", new_fm, count=1, flags=re.M)
        # 子分区
        if sub:
            if re.search(r"^zone_sub: ", new_fm, re.M):
                new_fm = re.sub(r"^zone_sub: .*$", f"zone_sub: {yaml_str(sub)}", new_fm, flags=re.M)
            else:
                new_fm = re.sub(r"^(zone: .*)$", lambda mm: f"{mm.group(1)}\nzone_sub: {yaml_str(sub)}", new_fm, count=1, flags=re.M)
        if not re.search(rf"^  - bilibili/zone/{re.escape(main)}$", new_fm, re.M) and \
                re.search(r"^  - bilibili/up$", new_fm, re.M):
            new_fm = re.sub(
                r"^(  - bilibili/up)$",
                lambda mm: f"{mm.group(1)}\n  - bilibili/zone/{main}",
                new_fm, count=1, flags=re.M,
            )
        if new_fm != fm:
            changed = True

    # ---- 正文：「主分区」行加在「主页」行后 ----
    desc_line = f"- **主分区**：{desc}"
    if "- **主分区**：" in body:
        if f"- **主分区**：{desc}" not in body:
            body = re.sub(r"- \*\*主分区\*\*：.*", lambda mm: desc_line, body)
            changed = True
    elif "- **主页**" in body:
        body = re.sub(
            r"^(- \*\*主页\*\*：.*)$",
            lambda mm: f"{mm.group(1)}\n{desc_line}",
            body, count=1, flags=re.M,
        )
        changed = True

    if not changed:
        return False
    result = (new_fm + body) if new_fm is not None else body
    write_atomic(note_path, result)
    return True


def existing_note_map(*dirs: Path) -> dict[str, str]:
    """扫描已有笔记，建立「文件名小写 → mid」映射，用于同名 UP 去重。

    可以一次传多个目录：新版笔记按分区收在 `B站UP文件夹/<分区>/`，老版本散落在
    分区根目录或 `B站UP文件夹/` 扁平层，所以这里用 rglob 递归扫，层级怎么变都能找到。
    """
    mapping: dict[str, str] = {}
    for up_dir in dirs:
        if not up_dir or not up_dir.exists():
            continue
        for p in up_dir.rglob("*.md"):
            text = read_note(p)[:600]
            m = re.search(r'^mid:\s*"?([^"\n]+)"?', text, re.M)
            if m:
                mapping[p.stem.lower()] = m.group(1).strip()
    return mapping


# `![[_assets/covers/BV1xx.jpg|380]]` → `![[BV1xx.jpg|380]]`
_ASSET_EMBED = re.compile(r"!\[\[_assets/(?:covers|avatars)/([^\]|]+?)(\|[^\]]*)?\]\]")


def retarget_embeds(text: str) -> tuple[str, int]:
    """把「带 `_assets/` 前缀的图片嵌入」改成裸文件名，返回（新文本, 改动处数）。

    笔记挪进子文件夹后，`_assets/covers/x.jpg` 相对路径就指错了；而 Obsidian 对
    全库唯一的裸文件名始终能解析。封面按 BV 号、头像按 mid 命名，天然唯一。
    """
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        count += 1
        return f"![[{m.group(1)}{m.group(2) or ''}]]"

    return _ASSET_EMBED.sub(repl, text), count

# ════════════════════════════════════════════════════════════════════
# 11 / 20 · migrate —— 笔记目录整理：按分区归位、修双链与图片引用、重建总览
#    （原文件：bilisync/migrate.py）
# ════════════════════════════════════════════════════════════════════

"""目录结构迁移：把 UP 笔记按「分区 → UP」两级收进 `B站UP文件夹/`。

历史上有过两代结构，迁移会把它们统一到最新一代：

    第一代（扁平）           第二代（只有 UP 一层）        第三代（按分区，当前）
    08_B站关注/              08_B站关注/                   08_B站关注/
    ├── B站关注总览.md       ├── B站关注总览.md            ├── B站关注总览.md   ← 只链分区笔记
    ├── 老番茄.md            ├── B站UP文件夹/               ├── 收藏夹.md
    ├── 影视飓风.md          │   ├── 老番茄.md              ├── B站UP文件夹/
    └── _assets/             │   └── 影视飓风.md            │   ├── 科技.md     ← 分区笔记
                             └── _assets/                   │   ├── 科技/
                                                            │   │   └── 影视飓风.md
                                                            │   └── 未分区/
                                                            └── _assets/

迁移做四件事，全部幂等，可反复执行：
1. 把根目录里的 UP 笔记先收进 `B站UP文件夹/`；
2. 再按笔记 frontmatter 的 `zone` 把它们分到 `B站UP文件夹/<分区>/`
   （分区取不到时依次退到 state，最后落到「未分区」）；
3. 修笔记里的图片嵌入：`![[_assets/covers/BVxxx.jpg|380]]` → `![[BVxxx.jpg|380]]`；
4. 重建总览页（只链分区笔记）+ 各分区笔记（UP 双链的唯一来源）。

只移动、不删除；目标已存在时改名保留，绝不覆盖。
"""










MID_RE = re.compile(r'^mid:\s*"?([^"\n]+)"?', re.M)
ZONE_RE = re.compile(r'^zone:\s*"?([^"\r\n]+?)"?\s*$', re.M)
# 总览页里的笔记链接：[[名字|别名]] 或 [[名字]]
INDEX_LINK = re.compile(r"\[\[([^\]|#^]+?)(\\?\|[^\]]*)?\]\]")


def note_mid(path: Path) -> str:
    m = MID_RE.search(read_note(path)[:600])
    return (m.group(1) or "").strip() if m else ""


def note_meta(path: Path, state=None) -> tuple[str, str]:
    """读一篇笔记的 (mid, 分区)。frontmatter 优先，其次 state，最后空（→未分区）。"""
    head = read_note(path)[:600]
    mm = MID_RE.search(head)
    mid = (mm.group(1) or "").strip() if mm else ""
    mz = ZONE_RE.search(head)
    zone = (mz.group(1) or "").strip() if mz else ""
    if not zone and mid and state is not None:
        zone = ((state.data.get("ups") or {}).get(mid) or {}).get("zone") or ""
    return mid, zone


def _move_to(src: Path, dest_dir: Path, log) -> tuple[str, Path | None]:
    """搬一个文件到 dest_dir，返回（结果标签, 落点）。标签：moved / renamed。"""
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / src.name
    if not target.exists():
        shutil.move(str(src), str(target))
        return "moved", target

    # 目标已存在：同 mid 视为同一 UP 的旧副本，改名保留，不覆盖新版本
    src_mid, dst_mid = note_mid(src), note_mid(target)
    if src_mid and src_mid == dst_mid:
        alt = dest_dir / f"{src.stem} (旧 {src_mid}).md"
        shutil.move(str(src), str(alt))
        log(f"  ! {src.name}：{dest_dir.name}/ 里已有同一 UP 的笔记，旧副本改名为 {alt.name}")
        return "renamed", alt
    alt = dest_dir / f"{src.stem} ({src_mid or 'old'}).md"
    shutil.move(str(src), str(alt))
    log(f"  ! {src.name}：{dest_dir.name}/ 存在同名但不同 UP 的文件，本次改名 {alt.name}")
    return "renamed", alt


def _move_one(src: Path, ups_dir: Path, log) -> tuple[str, Path | None]:
    """把根目录的笔记搬进 `B站UP文件夹/`（第一代 → 第二代），仅此一步不分区。"""
    return _move_to(src, ups_dir, log)


def organize_by_zone(ups_dir: Path, state=None, log=print, dry_run: bool = False) -> dict:
    """按 frontmatter 的 zone 把笔记分进 `ups_dir/<分区>/`，幂等。

    已经在正确分区文件夹里的笔记不做任何改动（连文件时间都不碰）。
    """
    stats = {"moved": 0, "renamed": 0}
    if not ups_dir.exists():
        return stats

    for p in sorted(ups_dir.rglob("*.md")):
        if is_zone_note(p):
            continue  # 分区笔记放在 ups_dir 根（B站UP文件夹/科技.md），不是 UP，别动
        _, zone = note_meta(p, state)
        dest_dir = ups_dir / zone_dir(zone)
        if p.parent.resolve() == dest_dir.resolve():
            continue
        if dry_run:
            log(f"  [dry-run] {p.relative_to(ups_dir)} → {dest_dir.name}/")
            stats["moved"] += 1
            continue
        tag, dest = _move_to(p, dest_dir, log)
        stats[tag] += 1
        if tag == "moved":
            log(f"  · {p.name} → {dest_dir.name}/")

    # 搬空的旧分区文件夹顺手清掉（只清 ups_dir 下一层，不会碰 ups_dir 本身）
    # dry-run 只应「看」，不能有任何副作用（否则试运行也会动磁盘）
    if not dry_run:
        for d in ups_dir.iterdir():
            if d.is_dir() and not any(d.iterdir()):
                try:
                    d.rmdir()
                except OSError as exc:
                    log(f"  ! 空目录清理失败（不影响整理结果）：{d.name} —— {exc}")
    return stats


def _fix_embeds(paths: list[Path], log) -> int:
    fixed = 0
    for p in paths:
        text = read_note(p)
        if not text:
            continue
        new, n = retarget_embeds(text)
        if n:
            write_atomic(p, new)
            fixed += n
    if fixed:
        log(f"  ✓ 修正 {fixed} 处图片引用（改为裸文件名，不受笔记层级影响）")
    return fixed


def write_zone_notes(cfg: Config, rows: list[dict], log=print) -> int:
    """按 rows 里的分区逐个写「分区笔记」：`B站UP文件夹/<分区>.md`。

    - 分区笔记是 UP 双链的唯一来源：总览只链这里，反向链接/图谱按分区隔离；
    - 手写区（## 我的笔记）跨次保留；
    - 某分区一个 UP 都不剩时清理对应分区笔记（有手写内容则保留并提示）。
    返回写出的分区笔记数量。
    """
    ups_dir = cfg.vault.ups_dir
    ups_subdir = cfg.vault.ups_subdir
    index_name = cfg.vault.index_note.stem

    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r.get("zone") or ZONE_UNKNOWN, []).append(r)

    written = 0
    for z in sort_zones(groups.keys()):
        zpath = zone_note_path(ups_dir, z)
        manual = extract_manual(read_note(zpath))
        write_atomic(
            zpath,
            render_zone_note(
                z,
                groups[z],
                ups_subdir=ups_subdir,
                index_name=index_name,
                manual=manual,
            ),
        )
        written += 1

    # 清理已经没有 UP 的旧分区笔记（分区改了/UP 取关都会触发）
    keep = {zone_dir(z) for z in groups}
    for p in ups_dir.glob("*.md"):
        if not is_zone_note(p) or p.stem in keep:
            continue
        if extract_manual(read_note(p)):
            log(f"  ! 分区笔记 {p.name} 已无对应 UP，但里面有你手写的内容，已保留")
            continue
        log(f"  · 分区笔记 {p.name} 已无对应 UP（且无手写内容），删除")
        try:
            p.unlink()
        except OSError as exc:
            log(f"  ! 删除失败（不影响本轮）：{p.name} —— {exc}")
    return written


def _rebuild_index_from_state(cfg: Config, state, ups_dir: Path, log) -> bool:
    rows = []
    for mid, entry in (state.data.get("ups") or {}).items():
        name = entry.get("note_name")
        if not name or not find_note(ups_dir, name):
            continue
        rows.append(
            {
                "mid": mid,
                "uname": entry.get("uname", ""),
                "note_name": name,
                "zone": entry.get("zone") or "",
                "latest_pub": entry.get("latest_pub"),
                "latest_title": entry.get("latest_title", ""),
                "latest_url": entry.get("latest_url", ""),
                "updates_30d": state.recent_updates(mid),
            }
        )
    if not rows:
        return False
    rows.sort(key=lambda r: (r["latest_pub"] or ""), reverse=True)
    runs = state.data.get("runs") or []
    write_atomic(
        cfg.vault.index_note,
        render_index(
            rows=rows,
            last_run=runs[-1] if runs else None,
            runs=runs,
            ups_subdir=cfg.vault.ups_subdir,
            favs_note="收藏夹" if (cfg.vault.up_dir / "收藏夹.md").exists() else None,
        ),
    )
    zones = {r["zone"] or ZONE_UNKNOWN for r in rows}
    znotes = write_zone_notes(cfg, rows, log=log)
    log(
        f"  ✓ 总览页只链 {cfg.vault.ups_subdir}/<分区>.md 分区笔记"
        f"（{len(rows)} 个 UP / {len(zones)} 个分区 / {znotes} 篇分区笔记），"
        "UP 双链按分区隔离"
    )
    return True


def _rewrite_index_links(cfg: Config, ups_dir: Path, log) -> int:
    """没有 state 时的兜底：直接在总览页文本里给链接补「分区」前缀。"""
    path = cfg.vault.index_note
    text = read_note(path)
    if not text:
        return 0
    sub = cfg.vault.ups_subdir
    targets = {}
    for p in ups_dir.rglob("*.md"):
        if p.parent == ups_dir:  # 还没分区的老位置
            targets[p.stem] = f"{sub}/{p.stem}"
        else:
            targets[p.stem] = f"{sub}/{p.parent.name}/{p.stem}"
    changed = 0

    def repl(m: re.Match) -> str:
        nonlocal changed
        name, alias = m.group(1), m.group(2) or ""
        if "/" in name or name not in targets:
            return m.group(0)
        changed += 1
        return f"[[{targets[name]}{alias}]]"

    new = INDEX_LINK.sub(repl, text)
    if changed:
        write_atomic(path, new)
        log(f"  ✓ 总览页链接已补上分区目录（{changed} 处）")
    return changed


def migrate(
    cfg: Config,
    *,
    state=None,
    dry_run: bool = False,
    rebuild_index: bool = True,
    log=print,
) -> dict:
    root, ups_dir = cfg.vault.up_dir, cfg.vault.ups_dir
    stats = {"moved": 0, "renamed": 0, "zoned": 0, "embeds": 0, "index": 0}

    log(f"分区目录：{root}")
    log(f"UP 笔记目录：{ups_dir}")
    if not root.exists():
        log("✗ 分区目录不存在，先跑一次 run 再来迁移")
        return stats

    # 只搬「UP 笔记」：靠 frontmatter 里的 mid 认，绝不会把 收藏夹.md 之类的
    # 同目录笔记（没有 mid）当成 UP 搬走
    legacy = [
        p for p in root.glob("*.md")
        if p.name != cfg.vault.index_note.name and note_mid(p)
    ]
    log(f"根目录待迁移笔记：{len(legacy)} 篇")

    if dry_run:
        for p in legacy:
            log(f"  [dry-run] 将移动 {p.name} → {ups_dir.name}/")
        zstats = organize_by_zone(ups_dir, state, log=log, dry_run=True)
        stats["zoned"] = zstats["moved"]
        return stats

    ups_dir.mkdir(parents=True, exist_ok=True)
    for p in legacy:
        tag, dest = _move_one(p, ups_dir, log)
        stats[tag] += 1
        if tag != "moved":
            log(f"  · {p.name} → {dest.name if dest else '?'}")
    if stats["moved"] or stats["renamed"]:
        log(f"✓ 已移入 {ups_dir.name}/：{stats['moved'] + stats['renamed']} 篇")

    # 第二代 → 第三代：按 frontmatter 的 zone 分进子文件夹
    zstats = organize_by_zone(ups_dir, state, log=log)
    stats["zoned"] = zstats["moved"] + zstats["renamed"]
    if stats["zoned"]:
        log(f"✓ 已按分区归位：{stats['zoned']} 篇")

    # 全部笔记（含以前就在分区文件夹里的）都统一修一遍引用
    stats["embeds"] = _fix_embeds(sorted(ups_dir.rglob("*.md")), log)

    if rebuild_index:
        done = False
        if state is not None:
            done = _rebuild_index_from_state(cfg, state, ups_dir, log)
        if not done:
            stats["index"] = _rewrite_index_links(cfg, ups_dir, log)
    return stats

# ════════════════════════════════════════════════════════════════════
# 12 / 20 · browser —— Playwright 封装：持久化 profile、复用登录态、反自动化探测
#    （原文件：bilisync/browser.py）
# ════════════════════════════════════════════════════════════════════

"""浏览器会话管理：持久化登录态 + 登录流程 + 轻量反自动化痕迹处理。

登录态靠 Playwright 的 launch_persistent_context：cookie 落在 .profile 目录里，
和日常浏览器完全隔离，首次扫码之后长期有效（B 站 cookie 有效期以月计，
真正跑不动时 `run.bat login` 重扫一次即可）。
"""
















NAV_API = "https://api.bilibili.com/x/web-interface/nav"
HOME_URL = "https://www.bilibili.com/"
LOGIN_URL = "https://passport.bilibili.com/login"  # 直达扫码登录页（首页只弹「立即登录」下拉，不出二维码）

# 用真实 Chrome 的 UA，避免 HeadlessChrome 字样被风控识别
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

# 并发工作实例与主实例共用的 chromium 参数
CHROMIUM_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-features=Translate,OptimizationHints",
    "--no-first-run",
    "--no-default-browser-check",
]

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
window.chrome = window.chrome || {runtime: {}};
"""


class LoginRequired(RuntimeError):
    """未登录，且当前不允许交互式登录（例如定时任务里）。"""


@contextmanager
def browser_session(cfg: Config, *, headless: bool | None = None) -> Iterator[BrowserContext]:
    cfg.profile_dir.mkdir(parents=True, exist_ok=True)
    with _sync_playwright()() as pw:
        try:
            context = _launch(pw, cfg, headless)
        except Exception as exc:
            # 缺浏览器内核的情况 _launch 内部已经处理过，重试也没用
            if _browser_missing(exc):
                raise
            # 大概率是上次被强杀后 chromium 残留、占着 .profile，清掉再试一次
            kill_stale_browser(str(cfg.profile_expanded))
            context = _launch(pw, cfg, headless)
        context.set_default_timeout(cfg.scrape.timeout_ms)
        context.add_init_script(STEALTH_JS)
        try:
            yield context
        finally:
            context.close()


def _launch(pw, cfg: Config, headless: bool | None) -> BrowserContext:
    try:
        return _start_context(pw, cfg, headless)
    except Exception as exc:
        # 换个电脑/新装的 exe 上没有浏览器内核时，playwright 只会抛一句英文错误。
        # 这里直接用它自带的 driver 把 chromium 下下来，再重试一次，用户无需装 Python。
        if not _browser_missing(exc):
            raise
        if not install_chromium():
            raise RuntimeError(
                "缺少 Chromium 浏览器内核，且自动下载失败。\n"
                "  手动安装：python -m playwright install chromium\n"
                "  国内网络可先设镜像：set PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright"
            ) from exc
        return _start_context(pw, cfg, headless)


def _browser_missing(exc: BaseException) -> bool:
    """判断异常是不是「浏览器没装」（而不是页面/超时之类的运行时错误）。"""
    text = str(exc)
    return "Executable doesn't exist" in text or "playwright install" in text.lower()


def install_chromium(log=print) -> bool:
    """调用 playwright 自带 driver 下载 chromium（仅缺浏览器时使用）。

    打包成 exe 后 driver（node.exe + cli.js）就在包内，所以这条命令不依赖
    外部 Python 环境；先走官方源，失败再用国内镜像重试一次。
    """
    try:
        from playwright._impl._driver import compute_driver_executable

        entry = compute_driver_executable()
        cmd = [str(p) for p in (entry if isinstance(entry, (list, tuple)) else [entry])]
    except Exception as exc:
        log(f"× 无法定位 playwright driver：{exc}")
        return False

    mirrors = [None, "https://cdn.npmmirror.com/binaries/playwright"]
    for idx, host in enumerate(mirrors, 1):
        env = dict(os.environ)
        if host:
            env["PLAYWRIGHT_DOWNLOAD_HOST"] = host
        tip = "官方源" if not host else "国内镜像"
        log(f"· 未检测到浏览器内核，正在从{tip}下载 chromium（约 150 MB，只需一次）…")
        log("  （下载进度会实时显示；卡住不动超过 20 秒会提示，可 Ctrl+C 中断）")
        ok = _run_installer([*cmd, "install", "chromium"], env=env, log=log, tip=tip)
        if ok:
            log("\n✓ 浏览器内核已就绪")
            return True
        if idx < len(mirrors):
            log("· 换国内镜像重试…")
    return False


def _run_installer(cmd: list[str], *, env: dict, log=print, tip: str = "") -> bool:
    """执行 playwright install，并把下载进度实时打到控制台。

    playwright 的进度条用 \\r 刷新且不换行，所以这里按块读取原样输出；
    另起一个心跳线程，长时间没有输出时提示「还在下载」，避免看起来像卡死。
    """
    import sys
    import threading

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, env=env, bufsize=0,
        )
    except Exception as exc:
        log(f"  × 启动下载器失败：{exc}")
        return False

    started = time.time()
    last_output = [started]
    done = threading.Event()

    def heartbeat() -> None:
        while not done.wait(5):
            idle = time.time() - last_output[0]
            if idle >= 20:
                log(f"  …已等待 {int(time.time() - started)} 秒，仍无新进度（网络较慢，继续等待）")
                last_output[0] = time.time()

    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        while True:
            chunk = proc.stdout.read(256) if proc.stdout else b""
            if chunk:
                text = chunk.decode("utf-8", "replace") if isinstance(chunk, bytes) else chunk
                sys.stdout.write(text)
                sys.stdout.flush()
                last_output[0] = time.time()
            elif proc.poll() is not None:
                break
            else:
                time.sleep(0.1)
    except KeyboardInterrupt:
        proc.kill()
        done.set()
        log("\n· 已取消下载")
        return False
    finally:
        done.set()
    if not sys.stdout.isatty():
        sys.stdout.write("\n")
    code = proc.wait()
    if code != 0:
        log(f"  × 下载失败（{tip}，退出码 {code}）")
        return False
    return True


def _start_context(pw, cfg: Config, headless: bool | None) -> BrowserContext:
    return pw.chromium.launch_persistent_context(
        user_data_dir=cfg.profile_expanded,
        headless=cfg.scrape.headless if headless is None else headless,
        viewport={"width": 1440, "height": 900},
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        user_agent=UA,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-features=Translate,OptimizationHints",
            "--no-first-run",
            "--no-default-browser-check",
        ],
        ignore_default_args=["--enable-automation"],
    )


def export_storage_state(context: BrowserContext, path: Path) -> bool:
    """把登录态（cookie + localStorage）导出成 JSON，供并发工作实例共享。

    持久化 profile 目录同一时刻只能被一个 chromium 使用，并发实例不能共用
    .profile；导出成 storage_state 后，各工作实例用普通 context 挂同一份
    登录态即可，互不冲突。
    """
    try:
        context.storage_state(path=str(path))
        return Path(path).exists()
    except Exception:
        return False


def launch_worker_context(pw, cfg: Config, worker_id: int, cookies_path: Path) -> BrowserContext:
    """给并发工作线程开一个独立浏览器上下文。

    - cookies_path：export_storage_state 导出的登录态 JSON，启动后把其中的
      cookie 注入上下文（launch_persistent_context 不支持 storage_state 参数，
      手动 add_cookies 是官方兼容做法）；
    - worker_id 会以 --biliwatch-worker=N 注入命令行，工作实例卡死时
      监控线程靠这个标记精确杀掉它自己的 chromium，不误伤其他实例。
    """
    context = pw.chromium.launch_persistent_context(  # type: ignore[union-attr]
        user_data_dir=str(cfg.profile_dir.parent / f".profile-w{worker_id}"),
        headless=cfg.scrape.headless,
        viewport={"width": 1280, "height": 800},
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        user_agent=UA,
        args=CHROMIUM_ARGS + [f"--biliwatch-worker={worker_id}", "--window-size=1280,800"],
        ignore_default_args=["--enable-automation"],
    )
    cookies_file = Path(cookies_path)
    if cookies_file.exists():
        try:
            data = json.loads(cookies_file.read_text(encoding="utf-8"))
            cookies = data.get("cookies") or []
            if cookies:
                context.add_cookies(cookies)
        except Exception:
            pass  # 注入失败按匿名继续，后续会被风控重试逻辑兜住
    context.set_default_timeout(cfg.scrape.timeout_ms)
    context.add_init_script(STEALTH_JS)
    return context


def kill_stale_browser(profile_dir: str) -> None:
    """杀掉命令行里带着本项目 profile 路径的残留 chromium（只影响本项目，不碰日常浏览器）。"""
    marker = profile_dir.lower()
    try:
        ps = (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.Name -match 'chrome' -and $_.CommandLine "
            f"-like '*{marker}*' }} | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, timeout=30,
        )
        time.sleep(1.0)
    except Exception:
        pass


def nav_info(context: BrowserContext) -> dict:
    """用页面同源的 nav 接口判断登录态，比解析 DOM 稳定得多。"""
    try:
        resp = context.request.get(NAV_API, timeout=20000)
        payload = resp.json()
    except Exception as exc:  # 网络抖动/接口变更都当未登录处理
        return {"isLogin": False, "error": str(exc)}
    data = payload.get("data") or {}
    return {
        "isLogin": bool(data.get("isLogin")),
        "mid": str(data.get("mid") or ""),
        "uname": data.get("uname") or "",
        "vip": bool((data.get("vipStatus") or 0) == 1),
    }


def ensure_login_ready(cfg: Config, *, headless: bool, log=print, wait_seconds: int = 300) -> dict:
    """确保已登录，且「已登录时绝不弹窗」。

    headless=True（后台/无人值守）时的正确姿势：
      1. 先用无窗口会话静默探一次登录态；
      2. 已登录 → 直接返回，用户全程看不到窗口；
      3. 未登录 → 才单独开一个有窗口的会话等扫码，扫完 **立即关闭** 这个窗口，
         后续抓取仍在无窗口会话里进行。

    headless=False 时窗口本来就该可见，直接返回空 dict 让调用方在原会话里处理登录
    （避免多开一次浏览器）。
    """
    if not headless:
        return {}

    with browser_session(cfg, headless=True) as ctx:
        info = nav_info(ctx)
    if info.get("isLogin"):
        return info

    log("· 登录态无效或已过期，打开浏览器窗口等待扫码（扫完自动关闭窗口）…")
    with browser_session(cfg, headless=False) as ctx:
        info = ensure_login(ctx, interactive=True, wait_seconds=wait_seconds)
    log("✓ 登录成功，扫码窗口已关闭")
    return info


def ensure_login(context: BrowserContext, *, interactive: bool, wait_seconds: int = 300) -> dict:
    """确保处于登录态；interactive=True 时打开首页等用户扫码。"""
    info = nav_info(context)
    if info.get("isLogin"):
        return info

    if not interactive:
        raise LoginRequired(
            "登录态已失效。请先手动执行一次 `run.bat login` 扫码登录，"
            "再让定时任务继续跑（定时任务不会弹窗打扰你）。"
        )

    page = context.pages[0] if context.pages else context.new_page()
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    try:
        # 万一被风控跳回首页，点一下「登录」把二维码面板拉出来
        if "passport.bilibili.com" not in page.url:
            page.click("text=登录", timeout=3000)
            page.wait_for_timeout(1200)
    except Exception:
        pass  # 点不到也不阻塞，反正窗口里用户可以自己点
    print("\n" + "=" * 58)
    print("需要登录：请在刚打开的浏览器窗口里扫码登录 B 站（应已自动打开二维码页）")
    print(f"登录完成后会自动继续，最多等待 {wait_seconds // 60} 分钟…")
    print("=" * 58 + "\n")

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        time.sleep(3)
        info = nav_info(context)
        if info.get("isLogin"):
            print(f"登录成功：{info.get('uname')}（UID {info.get('mid')}）\n")
            return info
    raise LoginRequired(f"等待登录超时（{wait_seconds // 60} 分钟），本次运行终止。")


def human_pause(cfg: Config, scale: float = 1.0) -> None:
    time.sleep(random.uniform(cfg.scrape.delay_min, cfg.scrape.delay_max) * scale)

# ════════════════════════════════════════════════════════════════════
# 13 / 20 · scrape —— 抓取层：关注名单、UP 投稿列表、封面/头像下载
#    （原文件：bilisync/scrape.py）
# ════════════════════════════════════════════════════════════════════

"""页面抓取层：关注列表 → 每个 UP 的最新投稿 → 封面/头像下载。

只用 DOM 解析，不碰任何需要签名计算的私有接口 —— 走的就是浏览器里能看到的页面，
所以改版的风险落在选择器上，选择器集中在本文件，坏了只改这里。
"""













# 翻页上限，纯防御：246 个关注 = 11 页，60 页足够兜住 1400 个关注
MAX_FOLLOW_PAGES = 60

# 关注页里混进来的导航锚点，避免被当成 UP 名
NAME_BLACKLIST = {
    "主页", "动态", "投稿", "合集和系列", "关注", "粉丝", "关注数", "粉丝数",
    "TA的视频", "TA的动态", "视频", "图文", "音频", "全部", "搜索",
}

# 收集当前页所有 UP：mid → 该 UP 卡片里出现的所有文本片段。
# 名字的筛选（黑名单/长度）放在 Python 侧做，保证规则只有一处。
FOLLOW_ITEMS_JS = r"""
(myMid) => {
  const out = new Map();
  document.querySelectorAll('a[href*="space.bilibili.com/"]').forEach(a => {
    const m = (a.getAttribute('href') || '').match(/space\.bilibili\.com\/(\d+)/);
    if (!m) return;
    const mid = m[1];
    if (mid === myMid) return;
    const texts = (a.innerText || '').split('\n').map(s => s.trim()).filter(Boolean);
    if (!out.has(mid)) out.set(mid, []);
    out.get(mid).push(...texts);
  });
  return [...out.entries()];
}
"""

# 分页器信息：页面上明写「共 11 页 / 246 个」，用它做总量校验
FOLLOW_PAGER_JS = r"""
() => {
  const t = document.body.innerText || '';
  const m = t.match(/共\s*(\d+)\s*页\s*[\/|、]?\s*(\d+)?\s*个/);
  const btns = [...document.querySelectorAll('button')];
  const nums = btns
    .filter(b => /^\d+$/.test((b.innerText || '').trim()))
    .map(b => Number(b.innerText.trim()));
  const next = btns.find(b => (b.innerText || '').trim() === '下一页');
  const activeBtn = btns.find(
    b => /active/.test(b.className || '') && /^\d+$/.test((b.innerText || '').trim())
  );
  return {
    text: m ? m[0] : '',
    active: activeBtn ? Number(activeBtn.innerText.trim()) : null,
    pages: m ? Number(m[1]) : (nums.length ? Math.max(...nums) : null),
    count: m && m[2] ? Number(m[2]) : null,
    hasNext: !!next,
    nextDisabled: next ? /disabled/.test(next.className || '') : true,
  };
}
"""

# 当前页的 mid 指纹，用来判断「点下一页后内容真的换了」
PAGE_SIGNATURE_JS = r"""
() => {
  const s = [...document.querySelectorAll('a[href*="space.bilibili.com/"]')]
    .map(a => ((a.getAttribute('href') || '').match(/space\.bilibili\.com\/(\d+)/) || [])[1])
    .filter(Boolean);
  return [...new Set(s)].join(',');
}
"""

VIDEOS_JS = r"""
() => {
  const out = [];
  const cards = document.querySelectorAll('.bili-video-card, .upload-video-card');
  cards.forEach(card => {
    const a = card.querySelector('a.bili-cover-card') || card.querySelector('a[href*="/video/BV"]');
    if (!a) return;
    const href = a.getAttribute('href') || '';
    const m = href.match(/\/video\/(BV[0-9A-Za-z]{6,})/);
    if (!m) return;
    const img = card.querySelector('.bili-cover-card__thumbnail img') || card.querySelector('img');
    const titleEl = card.querySelector('.bili-video-card__title') || card.querySelector('[class*="title"]');
    const title = ((titleEl && (titleEl.getAttribute('title') || titleEl.innerText)) || (img && img.alt) || '').trim();
    const sub = card.querySelector('.bili-video-card__subtitle') || card.querySelector('[class*="subtitle"]');
    const dateText = sub ? (sub.innerText || '').trim().split('\n')[0] : '';
    let duration = '';
    card.querySelectorAll('.bili-cover-card__stats span, [class*="stats"] span').forEach(s => {
      const t = (s.innerText || '').trim();
      if (/^\d{1,2}:\d{2}(:\d{2})?$/.test(t)) duration = t;
    });
    out.push({
      bv: m[1],
      title: title,
      date_text: dateText,
      duration: duration,
      cover: img ? (img.getAttribute('src') || img.src || '') : '',
    });
  });
  return out;
}
"""

AVATAR_JS = r"""
() => {
  const img = document.querySelector('.bili-avatar img, .h-avatar img, .up-avatar img, img[class*="avatar"]');
  if (img) return img.getAttribute('src') || img.src || '';
  // 新版空间页头像可能是背景图
  for (const e of document.querySelectorAll('[class*="avatar"], [class*="face"]')) {
    const bg = getComputedStyle(e).backgroundImage || '';
    const m = bg.match(/url\(["']?(https?:)?\/\/[^"')]+/);
    if (m) return m[0].replace(/url\(["']?/, '');
  }
  return '';
}
"""


def space_video_url(mid: str) -> str:
    return f"https://space.bilibili.com/{mid}/upload/video"


def follow_url(mid: str) -> str:
    return f"https://space.bilibili.com/{mid}/fans/follow?tagid=-1"


def norm_url(src: str | None) -> str:
    """协议相对地址 / 图片尺寸后缀统一处理。"""
    if not src:
        return ""
    src = src.strip()
    if src.startswith("//"):
        src = "https:" + src
    # 去掉 @672w_378h_1c.webp 这类 CDN 缩放参数，拿原图
    return src.split("@", 1)[0]


def parse_pub_date(text: str) -> str | None:
    """把 B 站的相对时间/无年份日期统一成 YYYY-MM-DD。"""
    if not text:
        return None
    t = text.strip()
    today = date.today()

    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    if t.startswith("今天") or t.startswith("刚刚"):
        return today.isoformat()
    if t.startswith("昨天"):
        return (today - timedelta(days=1)).isoformat()
    if t.startswith("前天"):
        return (today - timedelta(days=2)).isoformat()

    m = re.match(r"(\d+)\s*分钟前", t)
    if m:
        return today.isoformat()
    m = re.match(r"(\d+)\s*小时前", t)
    if m:
        return today.isoformat()
    m = re.match(r"(\d+)\s*天前", t)
    if m:
        return (today - timedelta(days=int(m.group(1)))).isoformat()
    m = re.match(r"(\d+)\s*(周|星期)前", t)
    if m:
        return (today - timedelta(weeks=int(m.group(1)))).isoformat()

    # 10月17日 / 10-17（无年份：月份比当前大则为去年）
    m = re.match(r"(\d{1,2})[月-](\d{1,2})日?", t)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = today.year if month <= today.month else today.year - 1
        try:
            d = date(year, month, day)
            if d > today:
                # 无年份的日期不可能在未来：只可能是去年的（1 月初看到「12-30」之类）
                d = date(year - 1, month, day)
            return d.isoformat()
        except ValueError:
            return None
    return None


def _pick_name(candidates: list[str]) -> str:
    """一张卡片里会同时出现昵称、简介、"已关注"，挑第一个像昵称的。"""
    for name in candidates:
        if not name or len(name) > 24 or name in NAME_BLACKLIST:
            continue
        return name
    return ""


def _collect_page(page: Page, my_mid: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for mid, candidates in page.evaluate(FOLLOW_ITEMS_JS, my_mid):
        name = _pick_name(candidates)
        if name:
            out[mid] = name
        else:
            out.setdefault(mid, "")
    return out


def _click_next(page: Page) -> bool:
    """点「下一页」，用「激活页码」+「列表指纹」双重判定是否真的翻过去了。

    只比对列表指纹会误判：偶尔点击被遮挡或列表重绘慢，指纹没变但其实已经翻页；
    反过来，页码变了列表还没渲染完，也不能算失败。
    """
    info = page.evaluate(FOLLOW_PAGER_JS)
    if not info.get("hasNext") or info.get("nextDisabled"):
        return False

    before_sig = page.evaluate(PAGE_SIGNATURE_JS)
    before_page = info.get("active")
    try:
        btn = page.locator("button", has_text="下一页").first
        btn.scroll_into_view_if_needed(timeout=4000)
        btn.click(timeout=8000)
    except Exception:
        return False

    for _ in range(48):  # 最多等 12 秒
        page.wait_for_timeout(250)
        if page.evaluate(PAGE_SIGNATURE_JS) != before_sig:
            return True
        now_page = page.evaluate(FOLLOW_PAGER_JS).get("active")
        if now_page and before_page and now_page != before_page:
            return True
    return False


def _scroll_collect(page: Page, my_mid: str, into: dict[str, str], rounds: int = 40) -> None:
    """没有分页器时的兜底：边滚边累加（不能只在最后取一次，虚拟列表会丢已滚过的项）。"""
    idle = 0
    for _ in range(rounds):
        before = len(into)
        page.mouse.move(700, 500)
        page.mouse.wheel(0, 2400)
        page.wait_for_timeout(900)
        into.update(_collect_page(page, my_mid))
        if len(into) <= before:
            idle += 1
            if idle >= 3:
                break
        else:
            idle = 0


def _followings_pass(page: Page, my_mid: str, log) -> tuple[dict[str, str], dict]:
    """从头翻到尾走一遍，返回（mid→昵称, 分页器信息）。"""
    page.goto(follow_url(my_mid), wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    pager = page.evaluate(FOLLOW_PAGER_JS)
    pages = pager.get("pages")
    log(
        f"[followings] 页面声明：{pages or '?'} 页 / "
        f"{pager.get('count') if pager.get('count') is not None else '?'} 个关注"
    )
    collected = _collect_page(page, my_mid)

    if pages is None:
        log("[followings] 未发现分页器，改用滚动加载")
        _scroll_collect(page, my_mid, collected)
        return collected, pager

    page_no = 1
    limit = min(pages, MAX_FOLLOW_PAGES)
    while page_no < limit:
        if not _click_next(page):
            log(f"[followings] 第 {page_no} 页翻页失败，本轮停止")
            break
        page_no += 1
        page.wait_for_timeout(random.randint(200, 550))
        collected.update(_collect_page(page, my_mid))
        if page_no % 2 == 0 or page_no == limit:
            log(f"[followings] 已读 {page_no}/{pages} 页，累计 {len(collected)} 个")
    return collected, pager


def fetch_followings(page: Page, my_mid: str, cfg: Config, log=print) -> tuple[list[dict], int | None]:
    """抓完整的关注列表。

    B 站关注页是 vui_pagenation 传统分页（默认每页 24 个，滚到底不会加载更多），
    必须逐页点「下一页」；页面底部写「共 11 页 / 246 个」，拿来做完整性校验。
    单轮翻页可能中途失败，所以不足声明数时整体重试一轮，取两轮里更完整的那份。
    """
    best_items: list[dict] = []
    best_declared: int | None = None

    for attempt in (1, 2):
        collected, pager = _followings_pass(page, my_mid, log)
        declared = pager.get("count")

        items = [{"mid": m, "uname": n} for m, n in collected.items() if n]
        if len(items) > len(best_items):
            best_items, best_declared = items, declared

        if not declared or len(items) >= declared:
            break
        if attempt == 1:
            wait = random.uniform(4.0, 8.0)
            log(f"[followings] 只拿到 {len(items)}/{declared} 个，{wait:.0f} 秒后整体重试一轮")
            time.sleep(wait)

    items, declared = best_items, best_declared
    if declared:
        if len(items) < declared:
            log(f"[followings] ⚠️ 最终 {len(items)} 个，少于页面声明的 {declared} 个（建议稍后再跑一次）")
        elif len(items) > declared:
            log(f"[followings] 抓取 {len(items)} 个，多于声明的 {declared} 个（去重后仍偏多，留意）")
        else:
            log(f"[followings] ✓ 数量与页面声明一致：{len(items)} 个")
    else:
        log(f"[followings] 未读到页面声明总数，实抓 {len(items)} 个")
    return items, declared


def fetch_videos(page: Page, up: dict, cfg: Config, log=print) -> tuple[list[dict], str]:
    """抓 UP 的投稿列表。

    注意：B 站空间页有风控，匿名单次访问经常返回空列表（页面显示"拼命加载中"或弹登录框）。
    所以首屏为空时重试一次 —— 登录态下命中率会高很多，但重试仍值得保留。
    """
    mid = up["mid"]
    avatar = ""
    for attempt in range(1, 3):
        page.goto(space_video_url(mid), wait_until="domcontentloaded")
        page.wait_for_timeout(2500 if attempt == 1 else 4000)
        # 只要最前面几条，轻微滚动触发懒加载即可，不必滚到底
        page.mouse.wheel(0, 900)
        page.wait_for_timeout(1200)

        cards = page.evaluate(VIDEOS_JS)
        try:
            avatar = norm_url(page.evaluate(AVATAR_JS)) or avatar
        except Exception:
            pass

        videos: list[dict] = []
        seen: set[str] = set()
        for c in cards:
            bv = c.get("bv")
            if not bv or bv in seen:
                continue
            seen.add(bv)
            videos.append(
                {
                    "bv": bv,
                    "title": (c.get("title") or "").strip(),
                    "pub_text": (c.get("date_text") or "").strip(),
                    "pub_date": parse_pub_date(c.get("date_text") or ""),
                    "duration": (c.get("duration") or "").strip(),
                    "cover_url": norm_url(c.get("cover")),
                    "url": f"https://www.bilibili.com/video/{bv}",
                }
            )
            if len(videos) >= cfg.scrape.videos_per_up:
                break

        if videos:
            return videos, avatar
        if attempt == 1:
            # 退避时间要够长：太短会被判成秒级重试，风控反而更严
            wait = random.uniform(6.0, 11.0)
            log(f"    {up.get('uname', mid)} 首屏为空，疑似风控，{wait:.0f} 秒后重试…")
            time.sleep(wait)

    return [], avatar


def download_image(ctx: BrowserContext, url: str, dest_stem: Path) -> Path | None:
    """下载图片到 dest_stem + 推断扩展名；成功返回最终路径。"""
    if not url:
        return None
    # 复用：同名图片已经下过就不再发请求（245 个 UP × 5 条 ≈ 1200 次/轮，省掉 95%）
    for ext in (".jpg", ".png", ".webp", ".gif"):
        cand = dest_stem.with_suffix(ext)
        try:
            if cand.exists() and cand.stat().st_size > 1024:
                return cand
        except OSError:
            pass
    try:
        resp = ctx.request.get(url, headers={"Referer": "https://www.bilibili.com/"}, timeout=30000)
        if not resp.ok:
            return None
        body = resp.body()
        if len(body) < 1024:
            return None
        ctype = (resp.headers or {}).get("content-type", "")
        ext = ".jpg"
        if "png" in ctype:
            ext = ".png"
        elif "webp" in ctype:
            ext = ".webp"
        elif "gif" in ctype:
            ext = ".gif"
        path = dest_stem.with_suffix(ext)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        return path
    except Exception:
        return None


def run_scrape(cfg: Config, up: dict, page: Page, ctx: BrowserContext, log=print) -> tuple[list[dict], Path | None, str]:
    """抓一个 UP 的视频列表和头像，顺带把封面下载到库内。"""
    videos, avatar_url = fetch_videos(page, up, cfg, log=log)
    avatar_path = None
    if avatar_url and cfg.scrape.download_avatars:
        avatar_path = download_image(ctx, avatar_url, cfg.vault.avatars_dir / up["mid"])
    return videos, avatar_path, avatar_url

# ════════════════════════════════════════════════════════════════════
# 14 / 20 · pool —— 并发调度：N 个浏览器实例并行 + 实例级看门狗
#    （原文件：bilisync/pool.py）
# ════════════════════════════════════════════════════════════════════

"""并发抓取池：N 个独立浏览器实例并行抓不同 UP 的投稿列表。

设计要点（为什么这样能"更快、更不容易卡死"）：

1. 每个 worker 一个独立 chromium 实例（独立 profile 目录 + 共享登录态），
   互不阻塞——之前单线程时，一个页面的 page.evaluate 假死就拖死全程。
2. worker 内置"实例级看门狗"：监控线程发现某实例超过 watchdog_seconds
   没动静，就按命令行里的 --biliwatch-worker=N 标记精确杀掉它自己的
   chromium。被杀实例的 Playwright 调用随即抛异常 → 该 UP 记为失败 →
   实例自动重启接着抓下一个。**毒页面只损失一个任务，不再拖死整批。**
3. 主线程单点写状态：worker 只负责抓（页面解析 + 封面/头像下载），把
   结果扔回队列；写笔记、更新 state.json 全在主线程做，无锁竞争。
4. 失败即跳过并记录：单个 UP 失败不影响其他任务；连续多个失败仍触发
   熔断（疑似风控），主流程提前收尾、保留断点。
5. 全局看门狗兜底：任何日志行都会喂狗；如果整个程序（含所有 worker）
   都静默超过 watchdog_seconds，仍由 pipeline 的全局看门狗强杀续跑。
"""

















class WorkerPool:
    _circuit_broken = False  # 熔断标志：由 on_result 回调（主线程）在触发熔断时置位

    def __init__(
        self,
        cfg: Config,
        *,
        cookies_path,
        log,            # 线程安全日志（pipeline._log，已喂全局看门狗）
        on_result,      # on_result(mid, uname, result|None, error|None) 在主线程回调
        is_paused,      # () -> bool，暂停时 worker 不领新任务
        tick=None,      # 主线程空闲间隙的回调（响应暂停键等），约每秒一次
        on_start=None,  # on_start(mid)：worker 真正开抓某个 UP 前回调（记录在办，供续跑判定）
    ):
        self.cfg = cfg
        self.cookies_path = cookies_path
        self.log = log
        self.on_result = on_result
        self.is_paused = is_paused
        self.tick = tick
        self.on_start = on_start

        self.jobs: queue.Queue = queue.Queue()
        self.results: queue.Queue = queue.Queue()
        self.abort = threading.Event()       # 熔断/收尾：所有 worker 停止领任务
        # 每个实例的心跳与在办任务（监控线程用）
        self.beats: list[float] = []
        self.active: list[str | None] = []

        self._threads: list[threading.Thread] = []

    # ---------- 对外 ----------

    def run(self, jobs: list[dict]) -> bool:
        """跑完所有任务，返回是否正常收尾（False = 熔断提前结束）。"""
        self._circuit_broken = False
        n = min(self.cfg.scrape.workers, len(jobs))
        for j in jobs:
            self.jobs.put(j)
        self.beats = [time.time()] * n
        self.active = [None] * n

        for wid in range(n):
            t = threading.Thread(target=self._worker, args=(wid,), daemon=True, name=f"bili-worker-{wid}")
            t.start()
            self._threads.append(t)
            # 错峰启动，降低瞬间并发请求的风控特征
            time.sleep(random.uniform(1.5, 3.0))

        monitor = threading.Thread(target=self._monitor_loop, args=(n,), daemon=True, name="bili-worker-watchdog")
        monitor.start()

        dispatched = len(jobs)
        done = 0
        aborted = False
        while done < dispatched:
            if self.tick:
                try:
                    self.tick()
                except Exception:
                    pass
            try:
                mid, uname, result, error = self.results.get(timeout=1.0)
            except queue.Empty:
                # 所有 worker 都退场但结果没凑齐（理论上不该发生）→ 防御性退出
                if not any(t.is_alive() for t in self._threads):
                    self.log("[pool] 工作线程全部退出但任务未收齐，提前收尾")
                    aborted = True
                    break
                continue
            self.on_result(mid, uname, result, error)
            done += 1
        self.abort.set()
        for t in self._threads:
            t.join(timeout=10)
        return not (aborted or self._circuit_broken)

    # ---------- worker ----------

    def _worker(self, wid: int) -> None:
        cfg = self.cfg
        pw = None
        context = None
        try:
            while not self.abort.is_set():
                # 暂停期间不领新任务（在办任务不受影响）
                while self.is_paused() and not self.abort.is_set():
                    self._beat(wid, None)
                    time.sleep(0.5)
                try:
                    job = self.jobs.get_nowait()
                except queue.Empty:
                    return  # 队列领完了，收工
                if self.abort.is_set():
                    self.results.put((job["mid"], job["uname"], None, RuntimeError("熔断：跳过剩余任务")))
                    continue

                mid, uname = job["mid"], job["uname"]
                self._beat(wid, mid)
                if self.on_start is not None:
                    try:
                        self.on_start(mid)
                    except Exception:
                        pass  # 认领失败不影响抓取
                if context is None:
                    try:
                        # 上一个 driver 还没停就重新 start()：旧 driver 会变成孤儿
                        # （context.close() 不会结束 node driver，只有 pw.stop() 才会）
                        if pw is not None:
                            try:
                                pw.stop()
                            except Exception:
                                pass
                            pw = None
                        pw = _sync_playwright()().start()
                        context = launch_worker_context(pw, cfg, wid, self.cookies_path)
                        self.log(f"[worker-{wid}] 浏览器实例已启动（并发实例 {wid + 1}）")
                    except Exception as exc:
                        self.log(f"[worker-{wid}] 浏览器启动失败：{exc}")
                        self.results.put((mid, uname, None, exc))
                        return

                page = context.new_page()
                try:
                    result = run_scrape(cfg, job, page, context, log=self.log)
                    # 顺带补分区：用刚抓到的最新一稿 BV 查官方分区（job 里带了 need_zone）
                    zone_info = None
                    if job.get("need_zone"):
                        try:
                            first_bv = (result[0] or [{}])[0].get("bv", "")
                            zone_info = fetch_up_zone(page, first_bv, log=self.log)
                            if zone_info:
                                self.log(f"[zone] {uname} —— {describe_zone(zone_info)}")
                        except Exception as exc:
                            self.log(f"[zone] {uname} 分区获取失败（不影响本轮抓取）：{exc}")
                    self.results.put((mid, uname, (result, zone_info), None))
                    # 实例间随机节流：并发后总请求频率 = N × 单机，节流别省
                    self._sleep_jitter(wid)
                except Exception as exc:
                    # 实例被监控线程杀掉时会走到这里：报错、记失败，实例重启续命
                    alive = False
                    try:
                        alive = context.browser is not None and context.browser.is_connected()
                    except Exception:
                        pass
                    if not alive:
                        self.log(f"[worker-{wid}] 浏览器实例已失联（看门狗重启），该 UP 记为失败")
                        try:
                            context.close()
                        except Exception:
                            pass
                        context = None
                        try:
                            pw.stop()          # 同步收掉 driver，否则每个失败 UP 漏一个 node 进程
                        except Exception:
                            pass
                        pw = None
                    self.results.put((mid, uname, None, exc))
                finally:
                    try:
                        page.close()
                    except Exception:
                        pass
                    self._beat(wid, None)
        finally:
            try:
                if context:
                    context.close()
            except Exception:
                pass
            try:
                if pw:
                    pw.stop()
            except Exception:
                pass

    def _sleep_jitter(self, wid: int) -> None:
        cfg = self.cfg
        end = time.time() + random.uniform(cfg.scrape.delay_min, cfg.scrape.delay_max)
        while time.time() < end and not self.abort.is_set():
            time.sleep(0.3)
            self._beat(wid, None)

    def _beat(self, wid: int, task: str | None) -> None:
        if 0 <= wid < len(self.beats):
            self.beats[wid] = time.time()
        if task is not None and 0 <= wid < len(self.active):
            self.active[wid] = task
        elif task is None and 0 <= wid < len(self.active):
            self.active[wid] = None

    # ---------- 实例级看门狗 ----------

    def _monitor_loop(self, n: int) -> None:
        timeout = self.cfg.scrape.watchdog_seconds
        while not self.abort.is_set():
            time.sleep(5)
            now = time.time()
            for wid in range(n):
                task = self.active[wid] if wid < len(self.active) else None
                if not task:
                    continue
                idle = now - (self.beats[wid] if wid < len(self.beats) else now)
                if idle > timeout:
                    self.log(
                        f"[watchdog-w{wid}] 实例 {wid} 抓 UP {task} 已 {int(idle)} 秒无响应，"
                        "重启该实例（此 UP 记为失败，下轮运行会重试）"
                    )
                    self._beat(wid, None)  # 先清心跳，避免重复触发
                    _kill_worker_browser(wid)


def _kill_worker_browser(worker_id: int) -> None:
    """按命令行标记精确杀掉指定 worker 的 chromium（不碰主实例和其他 worker）。"""
    marker = f"--biliwatch-worker={worker_id}"
    try:
        ps = (
            "Get-CimInstance Win32_Process | "
            f"Where-Object {{ $_.Name -match 'chrome' -and $_.CommandLine -like '*{marker}*' }} | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=30)
    except Exception:
        pass

# ════════════════════════════════════════════════════════════════════
# 15 / 20 · favs —— 收藏夹抓取：分区、封面缩略图、与 UP 笔记互链
#    （原文件：bilisync/favs.py）
# ════════════════════════════════════════════════════════════════════

"""B 站收藏夹 → Obsidian「收藏夹.md」。

抓取当前登录用户的所有收藏夹及其中视频，生成为**一篇纯 Markdown 笔记**
（本模块不产出任何 Word 文档）：
- 每个收藏夹一个二级标题，视频按收藏时间倒序、带递增序号；
- **每条带封面缩略图**（复用 `_assets/covers/BVxxx.jpg`，与 UP 笔记同一套命名，
  全库唯一，笔记挪位置也不会失效）；
- **每条带 `分区` + UP 双链**：UP 名指向 `B站UP文件夹/<分区>/xxx`；分区指向
  `B站UP文件夹/<分区>.md` 分区笔记（该分区笔记不存在时退化为普通文字）；
- 收藏夹里有、但**没关注的 UP**：自动在 `B站UP文件夹/未关注/` 建一篇占位笔记，
  这样每一条收藏都能双链跳转、在关系图里也能连起来（关注之后正式笔记优先接管链接）；
- 笔记尾部保留「我的笔记」手写区，重写时逐字回填（与 UP 笔记同一套标记）；
- 接口走 wbi.py 的共享签名方案（登录态页面内 fetch）。

链接语法全部用 Obsidian 原生双链：`[[路径/笔记|显示名]]`、`![[图片|宽度]]`。

分区来源优先级：state.ups（关注 UP 的分区标注结果）→ state.fav_ups（本模块缓存）
→ 现查 view 接口（用该 UP 在收藏夹里某一稿的 BV 换 tid）。查到的结果回写缓存，
所以只有第一次会走网络。

手动刷新：python BiliWatch_单文件版.py favs [--show] [--no-covers] [--refresh-zones]
"""











FAV_NOTE_NAME = "收藏夹"
# 未关注 UP 的占位笔记目录：B站UP文件夹/未关注/<UP名>.md
FAV_UNFOLLOWED = "未关注"

_FOLDERS_API = "https://api.bilibili.com/x/v3/fav/folder/created/list"
_RESOURCE_API = "https://api.bilibili.com/x/v3/fav/resource/list"
_SPACE_URL = "https://space.bilibili.com/{mid}"


# ---------------------------------------------------------------- 抓取


def _norm_media(m: dict) -> dict:
    """把接口返回的 media 压成渲染需要的字段（顺带把封面 URL 升到 https）。"""
    bv = m.get("bvid") or ""
    cover = m.get("cover") or ""
    if cover.startswith("http://"):
        cover = "https://" + cover[len("http://"):]
    upper = m.get("upper") or {}
    return {
        "bv": bv,
        "title": m.get("title") or "",
        "cover": cover,
        "mid": str(upper.get("mid") or ""),
        "uname": upper.get("name") or "",
        "fav_time": m.get("fav_time") or 0,
        "duration": m.get("duration"),
        "link": f"https://www.bilibili.com/video/{bv}" if bv else (m.get("link") or ""),
    }


def fetch_favorites(page, log=print) -> list[dict]:
    """抓取全部收藏夹及视频。返回 [{id, title, media_count, medias: [...]}]。"""
    wbi_keys = keys(page)
    nav_data = nav(page)
    my_mid = nav_data.get("mid")
    if not my_mid:
        raise RuntimeError("nav 接口未返回 mid，登录态可能失效")
    log(f"登录用户：{nav_data.get('uname') or my_mid}（UID {my_mid}）")

    # ---- 收藏夹列表（可能多页） ----
    folders: list[dict] = []
    pn = 1
    while True:
        data = signed_get(page, _FOLDERS_API, {"up_mid": my_mid, "pn": pn, "ps": 20}, wbi_keys)
        batch = data.get("list") or []
        folders.extend(batch)
        total = data.get("count") or len(folders)
        if len(folders) >= total or not batch:
            break
        pn += 1
        time.sleep(0.8)
    log(f"共 {len(folders)} 个收藏夹")

    # ---- 逐个收藏夹抓视频（每页 20 条，收藏时间倒序） ----
    result: list[dict] = []
    for f in folders:
        fid = f.get("id")
        title = f.get("title") or f"收藏夹{fid}"
        count = f.get("media_count") or 0
        log(f"  抓取收藏夹「{title}」（声明 {count} 条）...")
        medias: list[dict] = []
        pn = 1
        while True:
            data = signed_get(
                page,
                _RESOURCE_API,
                {"media_id": fid, "pn": pn, "ps": 20, "order": "mtime", "type": 0, "tid": 0, "platform": "web"},
                wbi_keys,
            )
            batch = data.get("medias") or []
            medias.extend(_norm_media(m) for m in batch)
            if len(medias) >= count or len(batch) < 20:
                break
            pn += 1
            time.sleep(0.8)
        result.append({"id": fid, "title": title, "media_count": count, "medias": medias})
        log(f"    ✓ 实际取到 {len(medias)} 条")
    return result


# ---------------------------------------------------------------- 分区解析


def _note_index(cfg: Config) -> dict[str, dict]:
    """mid → {name, zone, placeholder}，来自已存在的 UP 笔记（递归扫，兼容「分区/UP.md」层级）。

    只有笔记真的存在才给双链，否则 Obsidian 里会出现红色空链接、悬停也没有预览。
    zone 取笔记 frontmatter（与所在文件夹一致），因为双链必须写成
    `B站UP文件夹/<分区>/<名字>`。

    同一 mid 既有正式笔记（B站UP文件夹/<分区>/）又有占位笔记（B站UP文件夹/未关注/）时，
    **正式笔记优先** —— 关注之后收藏夹里的链接会自动切到正式笔记。
    """
    out: dict[str, dict] = {}
    if not cfg.vault.ups_dir.exists():
        return out
    for p in cfg.vault.ups_dir.rglob("*.md"):
        head = read_note(p)[:600]
        m = re.search(r'^mid:\s*"?([^"\n]+)"?', head, re.M)
        if not m:
            continue
        z = re.search(r'^zone:\s*"?([^"\r\n]+?)"?\s*$', head, re.M)
        zone = z.group(1).strip() if z else p.parent.name
        mid = m.group(1).strip()
        is_ph = p.parent.name == FAV_UNFOLLOWED
        old = out.get(mid)
        if old and (is_ph or not old.get("placeholder")):
            continue  # 已有正式笔记：占位笔记不再覆盖它
        out[mid] = {"name": p.stem, "zone": zone, "placeholder": is_ph}
    return out


def resolve_up_zones(
    folders: list[dict],
    state,
    page,
    note_index: dict[str, dict],
    log=print,
    refresh: bool = False,
) -> dict[str, dict]:
    """给收藏夹里出现的每个 UP 解析分区（主+子）与可链接的笔记。

    返回 {mid: {uname, zone, sub, note}}，note 为 {name, zone}（笔记不存在时为 None）。
    结果写入 state["fav_ups"] 缓存，下次直接命中、不再发请求。
    """
    wanted: dict[str, dict] = {}
    for f in folders:
        for m in f["medias"]:
            mid = m["mid"]
            if not mid:
                continue
            w = wanted.setdefault(mid, {"uname": m["uname"], "bvs": []})
            if m["bv"]:
                w["bvs"].append(m["bv"])

    ups = (state.data.get("ups") or {}) if state else {}
    cache = state.data.setdefault("fav_ups", {}) if state else {}

    info: dict[str, dict] = {}
    miss = 0
    for mid, w in wanted.items():
        merged: dict = {"uname": w["uname"], "zone": "", "sub": ""}
        u = ups.get(mid) or {}
        if u.get("zone"):
            merged.update(zone=u["zone"], sub=u.get("zone_sub") or "", uname=u.get("uname") or w["uname"])
        c = cache.get(mid) or {}
        if not merged["zone"] and c.get("zone") and not refresh:
            merged.update(zone=c["zone"], sub=c.get("zone_sub") or "", uname=c.get("uname") or w["uname"])
        if not merged["zone"]:
            got = fetch_up_zone(page, bvid=(w["bvs"] or [""])[0], mid=mid, log=log)
            time.sleep(0.6)
            if got:
                merged.update(zone=got["zone"], sub=got.get("sub") or "")
                if state:
                    state.set_fav_up(mid, {"uname": merged["uname"], "zone": merged["zone"], "sub": merged["sub"]})
            else:
                miss += 1
        merged["note"] = note_index.get(mid)
        info[mid] = merged

    known = sum(1 for v in info.values() if v["zone"])
    log(f"  分区：{known}/{len(info)} 个 UP 已识别" + (f"，{miss} 个待下次重试" if miss else ""))
    return info


# ---------------------------------------------------------------- 封面


def download_covers(ctx, folders: list[dict], covers_dir, log=print) -> dict[str, str]:
    """下载收藏视频封面到 `_assets/covers/BVxxx.jpg`，返回 {bv: 文件名}。

    已有同名文件（UP 笔记抓过同一稿、或上次已下过）直接复用，不重复请求。
    """
    index: dict[str, str] = {}
    if covers_dir.exists():
        for p in covers_dir.iterdir():
            if p.is_file():
                index.setdefault(p.stem, p.name)
    covers_dir.mkdir(parents=True, exist_ok=True)

    out: dict[str, str] = {}
    todo: list[dict] = []
    for f in folders:
        for m in f["medias"]:
            bv = m["bv"]
            if not bv:
                continue
            if bv in index:
                out[bv] = index[bv]
            else:
                todo.append(m)
    if todo:
        log(f"  下载封面 {len(todo)} 张...")
    for i, m in enumerate(todo, 1):
        saved = download_image(ctx, m["cover"], covers_dir / m["bv"])
        if saved:
            out[m["bv"]] = saved.name
            index[m["bv"]] = saved.name
        else:
            log(f"  [warn] 封面下载失败：{m['bv']} {(m['title'] or '')[:24]}")
        if i % 10 == 0 or i == len(todo):
            log(f"    封面 {i}/{len(todo)}")
        time.sleep(0.2)
    return out


# ---------------------------------------------------------------- 渲染


def _esc(text: str) -> str:
    """标题里的方括号会破坏 Markdown 链接，转义掉。"""
    return (text or "").replace("[", "\\[").replace("]", "\\]")


def _alias(text: str) -> str:
    """双链别名里的 `|` 会把链接截断，换成全角。"""
    return (text or "").replace("|", "｜").replace("[", "［").replace("]", "］")


def _up_ref(mid: str, uname: str, info: dict, ups_subdir: str) -> str:
    """UP 引用：有笔记给双链（分屏打开即见分区），没有就给空间主页链接。

    文档现在按「分区/UP」两级存放，所以链接必须带分区目录，
    只写 `B站UP文件夹/名字` 在 Obsidian 里会解析不到。
    """
    name = _alias(uname) or _alias((info or {}).get("uname") or "") or mid
    note = (info or {}).get("note") or {}
    if note.get("name"):
        return f"[[{note_relpath(ups_subdir, note.get('zone'), note['name'])}|{name}]]"
    if mid:
        return f"[{name}]({_SPACE_URL.format(mid=mid)})"
    return name


def _duration(sec) -> str:
    if not isinstance(sec, int) or sec <= 0:
        return ""
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h} 小时 {m:02d} 分"
    return f"{m} 分 {s:02d} 秒"


def _fav_videos_by_up(folders: list[dict]) -> dict[str, list[dict]]:
    """mid → 该 UP 在收藏夹里出现的视频（按收藏时间倒序）。"""
    out: dict[str, list[dict]] = {}
    for f in folders:
        for m in f["medias"]:
            mid = m.get("mid")
            if mid:
                out.setdefault(mid, []).append(m)
    for vids in out.values():
        vids.sort(key=lambda v: v.get("fav_time") or 0, reverse=True)
    return out


def render_unfollowed_note(
    *,
    mid: str,
    uname: str,
    videos: list[dict],
    zone_txt: str = "",
    url: str = "",
    covers: dict[str, str] | None = None,
    cover_width: int = 0,
    manual: str = "",
) -> str:
    """未关注 UP 的占位笔记：能被双链解析、能看主页与分区、能记笔记。"""
    covers = covers or {}
    name = uname or f"UP_{mid}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    link = url or _SPACE_URL.format(mid=mid)
    rows = [
        "| 项 | 内容 |",
        "| --- | --- |",
        f"| 空间主页 | [打开 B 站主页]({link}) |",
        f"| UID | `{mid}` |",
        f"| 主分区 | {zone_txt or '未识别'} |",
        f"| 收藏的视频 | {len(videos)} 条 |",
    ]
    lines = [
        "---",
        "type: bilibili-up",
        "followed: false",
        "source: 收藏夹",
        f"uname: {name}",
        f'mid: "{mid}"',
        f'url: "{link}"',
        f"zone: {FAV_UNFOLLOWED}",
        f"updated: {now}",
        "---",
        "",
        f"# {name}",
        "",
        "> 这是一篇**占位笔记**：你收藏过 TA 的视频，但 TA 不在你的关注列表里，",
        "> 为了让收藏夹里的每条记录都能双链跳转，脚本自动建了这一篇。",
        "> 关注 TA 并运行一次抓取后，正式笔记会出现在对应分区目录，",
        "> 收藏夹里的链接会自动切到正式笔记；这一篇可以留着也可以删掉。",
        "",
        *rows,
        "",
        f"## 收藏夹里的视频（{len(videos)} 条）",
        "",
    ]
    for i, v in enumerate(videos, 1):
        title = _esc(v.get("title") or "(无标题)")
        vurl = v.get("link") or ""
        lines.append(f"{i}. **[{title}]({vurl})**  " if vurl else f"{i}. **{title}**  ")
        cover = covers.get(v.get("bv") or "")
        if cover and cover_width > 0:
            lines.append(f"    ![[{cover}|{cover_width}]]  ")
        meta = []
        if v.get("fav_time"):
            meta.append("收藏 " + datetime.fromtimestamp(v["fav_time"]).strftime("%Y-%m-%d"))
        dur = _duration(v.get("duration"))
        if dur:
            meta.append(dur)
        if meta:
            lines.append("    " + " · ".join(meta) + "  ")
        lines.append("")

    lines += [MANUAL_HEADING, MANUAL_BEGIN]
    if manual:
        lines += ["", manual]
    else:
        lines += ["", MANUAL_PLACEHOLDER]
    lines += ["", MANUAL_END, ""]
    return "\n".join(lines)


def ensure_unfollowed_notes(
    cfg: Config,
    folders: list[dict],
    up_info: dict[str, dict],
    taken: dict[str, str],
    followed_mids: set[str],
    covers: dict[str, str] | None = None,
    log=print,
) -> int:
    """给「收藏夹里有、但没关注也没笔记」的 UP 建占位笔记（幂等）。

    返回新建/更新的篇数。已有关注的 UP（正式笔记会由 run 生成）不在这里处理，
    避免和正式笔记抢同一个 mid。
    """
    videos_by_up = _fav_videos_by_up(folders)
    made = 0
    for mid, videos in videos_by_up.items():
        if not mid or mid in followed_mids:
            continue
        info = up_info.get(mid) or {}
        note = info.get("note") or {}
        if note and not note.get("placeholder"):
            continue  # 已有正式笔记
        uname = info.get("uname") or (videos[0].get("uname") if videos else "") or ""
        if note.get("name"):
            name = note["name"]
        else:
            name = safe_filename(uname, mid, taken)
        taken[name.lower()] = mid
        path = note_path(cfg.vault.ups_dir, FAV_UNFOLLOWED, name)
        old = read_note(path)
        content = render_unfollowed_note(
            mid=mid,
            uname=uname,
            videos=videos,
            zone_txt=describe_zone({"zone": info.get("zone") or "", "sub": info.get("sub") or ""})
            if info.get("zone")
            else "",
            covers=covers or {},
            cover_width=cfg.favs.cover_width,
            manual=extract_manual(old),
        )
        if content != old:
            # 只有 updated 时间戳不同就不重写：免得每次运行都刷新全部占位笔记的修改时间
            same = old and re.sub(r"^updated:.*$", "", old, count=1, flags=re.M) == re.sub(
                r"^updated:.*$", "", content, count=1, flags=re.M
            )
            if not same:
                try:
                    write_atomic(path, content)
                    made += 1
                except Exception as exc:  # 占位笔记写不进去不该影响收藏夹正文
                    log(f"  [warn] 占位笔记写入失败（{name}）：{exc}")
                    continue
        up_info.setdefault(mid, info)
        up_info[mid]["note"] = {"name": name, "zone": FAV_UNFOLLOWED, "placeholder": True}
    if made:
        log(f"  未关注 UP 占位笔记：{made} 篇（{cfg.vault.ups_subdir}/{FAV_UNFOLLOWED}/）")
    return made


def render_favs_note(
    folders: list[dict],
    manual: str = "",
    *,
    covers: dict[str, str] | None = None,
    up_info: dict[str, dict] | None = None,
    ups_subdir: str = "B站UP文件夹",
    cover_width: int = 320,
    linked_zones: set[str] | None = None,
) -> str:
    """把收藏夹数据渲染成一篇 Obsidian 笔记（含手写区）。"""
    covers = covers or {}
    up_info = up_info or {}
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = sum(len(f["medias"]) for f in folders)
    shown = sum(1 for f in folders for m in f["medias"] if covers.get(m["bv"]))

    lines = [
        "---",
        "type: bilibili-favs",
        "tags:",
        "  - bilibili",
        "  - bilibili/favs",
        f"updated: {now}",
        f"folders: {len(folders)}",
        f"videos: {total}",
        "---",
        "",
        "# 收藏夹",
        "",
        f"> 由 `bili-watch` 自动抓取（{now}），共 {len(folders)} 个收藏夹 / {total} 条视频"
        + (f"，{shown} 条带封面" if shown else "")
        + "。",
        "> 每条结构：标题 → 封面缩略图 → UP · `分区` · 收藏日期 · 时长（封面用 `![[图片|宽度]]` 嵌入）。",
        "> `分区` 是该 UP 的主分区（按其最新投稿归属）；分区名若能对上分区笔记，会写成双链，点开即到该区全部 UP。",
        f"> UP 名是双链，点开（或悬停预览）会在分屏里打开 `{ups_subdir}/<分区>/` 下的笔记，"
        "首屏即「主分区」。",
        "> 收藏过但**没关注**的 UP 也有双链：脚本会在 "
        f"`{ups_subdir}/{FAV_UNFOLLOWED}/` 下建一篇占位笔记（主页 / 分区 / 收藏的视频都记在里面）。",
        "手动刷新：`python BiliWatch_单文件版.py favs`。「我的笔记」手写区不会被覆盖。",
        "",
    ]

    for f in folders:
        medias = f["medias"]
        lines += [f"## {f['title']}（{len(medias)} 条）", ""]
        if not medias:
            lines += ["（空收藏夹或未取到数据）", ""]
            continue

        # 分区分布：一眼看清这个收藏夹都收了哪些频道
        tally: dict[str, int] = {}
        for m in medias:
            z = (up_info.get(m["mid"]) or {}).get("zone") or ""
            if z:
                tally[z] = tally.get(z, 0) + 1
        if tally:
            dist = " · ".join(f"{z} {n}" for z, n in sorted(tally.items(), key=lambda kv: -kv[1]))
            lines += [f"> 分区分布：{dist}", ""]

        for i, m in enumerate(medias, 1):
            title = _esc(m["title"] or "(无标题)")
            url = m["link"]
            # 行尾两个空格＝硬换行：即使开了「严格换行」，标题/图/元信息也不会挤成一段
            head = f"{i}. **[{title}]({url})**" if url else f"{i}. **{title}**"
            lines.append(head + "  ")

            cover = covers.get(m["bv"])
            if cover and cover_width > 0:
                lines.append(f"    ![[{cover}|{cover_width}]]  ")

            info = up_info.get(m["mid"]) or {}
            meta: list[str] = []
            up_name = m["uname"] or info.get("uname") or ""
            if up_name or m["mid"]:
                meta.append(_up_ref(m["mid"], up_name, info, ups_subdir))
            if info.get("zone"):
                ztxt = describe_zone({"zone": info["zone"], "sub": info.get("sub")})
                if info["zone"] in (linked_zones or set()):
                    # 分区笔记存在 → 用双链，点开就是这个区的全部 UP
                    meta.append(f"[[{zone_note_relpath(ups_subdir, info['zone'])}|{ztxt}]]")
                else:
                    meta.append(f"`{ztxt}`")
            else:
                meta.append("`分区未识别`")
            if m["fav_time"]:
                meta.append("收藏 " + datetime.fromtimestamp(m["fav_time"]).strftime("%Y-%m-%d"))
            dur = _duration(m["duration"])
            if dur:
                meta.append(dur)
            lines += ["    " + " · ".join(meta), ""]

    lines += [MANUAL_HEADING, MANUAL_BEGIN]
    if manual:
        lines += ["", manual]
    else:
        lines += ["", MANUAL_PLACEHOLDER]
    lines += ["", MANUAL_END, ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- 入口


def list_folders(page, log=print) -> list[dict]:
    """只获取收藏夹清单（名称/条数），不抓视频、不写笔记。

    供「获取收藏夹列表」这类快速检查用：几秒钟出结果，用来确认
    登录态有效、收藏夹结构没有变化，再决定要不要完整同步。
    """
    wbi_keys = keys(page)
    nav_data = nav(page)
    my_mid = nav_data.get("mid")
    if not my_mid:
        raise RuntimeError("nav 接口未返回 mid，登录态可能失效")
    log(f"登录用户：{nav_data.get('uname') or my_mid}（UID {my_mid}）")

    # 只要夹子列表，不要 medias（分页拉全，与 fetch_favorites 同一接口）
    folders: list[dict] = []
    pn = 1
    while True:
        data = signed_get(page, _FOLDERS_API, {"up_mid": my_mid, "pn": pn, "ps": 20}, wbi_keys)
        batch = data.get("list") or []
        folders.extend(batch)
        total = data.get("count") or len(folders)
        if len(folders) >= total or not batch:
            break
        pn += 1
        time.sleep(0.8)

    items = [
        {"id": f.get("id"), "title": f.get("title") or "", "media_count": f.get("media_count") or 0}
        for f in folders
    ]
    total = sum(f["media_count"] for f in items)
    log("")
    log(f"  收藏夹清单（{len(items)} 个 / 共 {total} 条视频）：")
    for f in items:
        log(f"   · {f['title']}  ——  {f['media_count']} 条  (id={f['id']})")
    log("")
    log("（以上为列表快照，未抓取视频内容；要抓正文请选任务 [3] 我的收藏夹）")
    return items


def sync_favs(
    cfg: Config,
    page,
    state=None,
    log=print,
    *,
    refresh_zones: bool = False,
    with_covers: bool | None = None,
) -> str:
    """抓取 + 写入「收藏夹.md」（带手写区保护）。返回文件路径。

    只写 Markdown：收藏夹.md + 未关注 UP 的占位笔记，不生成任何 Word 文档。
    """
    folders = fetch_favorites(page, log=log)
    note_path = cfg.vault.up_dir / f"{FAV_NOTE_NAME}.md"

    note_index = _note_index(cfg)
    up_info = resolve_up_zones(folders, state, page, note_index, log=log, refresh=refresh_zones)

    want_covers = cfg.favs.with_covers if with_covers is None else with_covers
    covers: dict[str, str] = {}
    if want_covers and cfg.favs.cover_width > 0:
        covers = download_covers(page.context, folders, cfg.vault.covers_dir, log=log)

    # 未关注的 UP 也建占位笔记：这样每条收藏都有可跳转的双链（幂等，不覆盖手写区）
    taken = existing_note_map(cfg.vault.ups_dir, cfg.vault.up_dir)
    followed = {str(u.get("mid")) for u in (state.followings if state else []) if u.get("mid")}
    ensure_unfollowed_notes(cfg, folders, up_info, taken, followed, covers=covers, log=log)

    # 已存在的分区笔记（B站UP文件夹/<分区>.md）→ 收藏夹里的分区名可以写成双链
    linked_zones = set()
    if cfg.vault.ups_dir.exists():
        for p in cfg.vault.ups_dir.glob("*.md"):
            if is_zone_note(p):
                linked_zones.add(p.stem)

    manual = extract_manual(read_note(note_path))
    write_atomic(
        note_path,
        render_favs_note(
            folders,
            manual,
            covers=covers,
            up_info=up_info,
            ups_subdir=cfg.vault.ups_subdir,
            cover_width=cfg.favs.cover_width,
            linked_zones=linked_zones,
        ),
    )
    if state:
        state.save()

    total = sum(len(f["medias"]) for f in folders)
    log(f"✓ 收藏夹笔记已写入：{note_path}")
    log(f"  共 {len(folders)} 个收藏夹 / {total} 条视频 / {len(covers)} 张封面")
    return str(note_path)

# ════════════════════════════════════════════════════════════════════
# 16 / 20 · followlist —— 关注名单缓存：followings.txt 读写（UID<TAB>昵称）
#    （原文件：bilisync/followlist.py）
# ════════════════════════════════════════════════════════════════════

"""关注名单 TXT：一次抓取、处处复用。

格式（UTF-8，每行一个 UP，# 开头为注释）：
    12345	老番茄
    67890	某UP主

即「UID <TAB> 昵称」。后续每次运行直接读本文件拿名单，不再每次都翻
11 页关注页（省 1~2 分钟，也少一次风控暴露）。名单的更新有两种方式：
- 手动：python BiliWatch_单文件版.py followings（单独抓一次名单）
- 自动：管道检测到 TXT 缺失 / 缓存超过 refresh_followings_days 天时，
  在正式抓取前自动重新拉一遍并重写 TXT。
"""







TXT_PATH = PROJECT_ROOT / "followings.txt"


def txt_path() -> Path:
    return TXT_PATH


def save_txt(items: list[dict], path: Path | None = None) -> Path:
    """把关注列表写成 TXT（mid <TAB> uname，按 mid 数值排序，稳定 diff 友好）。"""
    p = Path(path) if path else TXT_PATH
    lines = ["# B站关注名单：UID<TAB>昵称（本文件由程序维护，可手动编辑，UID 为准）"]
    for it in sorted(items, key=lambda x: int(x["mid"]) if str(x["mid"]).isdigit() else 0):
        lines.append(f"{it['mid']}\t{it.get('uname', '')}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def load_txt(path: Path | None = None) -> list[dict]:
    """读取名单；返回 [{mid, uname}]。文件缺失/为空/全是注释时返回 []。

    行格式容忍：允许全角 TAB、多空格分隔；UID 必须是纯数字。
    """
    p = Path(path) if path else TXT_PATH
    if not p.exists():
        return []
    items: list[dict] = []
    seen: set[str] = set()
    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for sep in ("\t", "　", " "):
            if sep in line:
                mid, _, uname = line.partition(sep)
                break
        else:
            mid, uname = line, ""
        mid = mid.strip()
        if not mid.isdigit() or mid in seen:
            continue
        seen.add(mid)
        items.append({"mid": mid, "uname": uname.strip()})
    return items

# ════════════════════════════════════════════════════════════════════
# 17 / 20 · pipeline —— 主流程编排：检测 → 登录 → 名单 → 并发抓取 → 写 Markdown 笔记
#    （原文件：bilisync/pipeline.py）
# ════════════════════════════════════════════════════════════════════

"""主流程编排：检测 Obsidian 库 → 登录 → 关注名单（TXT）→ 并发抓取 → 写 Markdown 笔记。

输出只有一种：Markdown。
  - 每个 UP 一篇笔记（按分区归到 B站UP文件夹/<分区>/）
  - 一篇总览页（B站关注总览.md）
  - 每个分区一篇分区笔记（B站UP文件夹/<分区>.md）
  - 收藏夹单独一篇（收藏夹.md，见 favs.py）

本程序**不生成任何 Word 文档**。Markdown 是纯文本，装没装 Obsidian、库存在与否
都不影响写入；目录缺失时由 prepare_obsidian() 整条创建。

关注名单（详见 followlist.py）：
  - 首次运行自动抓一次关注列表，存成 followings.txt（UID<TAB>昵称）
  - 之后每次运行直接读 TXT，省去翻页抓名单的时间与风控暴露
  - TXT 缺失或缓存超过 refresh_followings_days 天时自动在线刷新（自动更新）
  - 也可手动执行 `python BiliWatch_单文件版.py followings` 单独更新名单

并发抓取（详见 pool.py）：
  - N 个独立浏览器实例并行抓不同 UP（N = scrape.workers，默认 3）
  - 单实例卡死由实例级看门狗单独重启，不拖累其他实例
  - 单个 UP 失败即跳过并记入 logs/errors.log；连续失败触发熔断

控制台展示约定：
- 每个阶段以「[步骤 n/5]」横幅开始，随时能看出跑到哪一步；
- 每个 UP 一行进度（i/总数 + 新增数）；
- 超过 12 秒的等待都带倒计时输出，绝不静默；
- 运行中按 P 可暂停、再按 P（或 R）继续；
- 断点续跑：每个 UP 成功即落盘，被强杀后（exit 9）下次从断点继续，不重复已完成任务。
"""






















MAX_CONSECUTIVE_FAILS = 5
TOTAL_STEPS = 5

# 当前运行的看门狗实例（_log 会自动喂它）
_WD: Watchdog | None = None
_PAUSE: PauseController | None = None


def _log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    if _WD is not None:
        _WD.beat(line)
def _beat(msg: str) -> None:
    """只喂狗不刷屏（用于封面下载等短暂静默操作之间）。"""
    if _WD is not None:
        _WD.beat(msg)


def _error_log(msg: str) -> None:
    """错误独立成档：logs/errors.log，一行一条，方便事后核对哪些 UP 没抓到。"""
    try:
        log_dir = PROJECT_ROOT / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "errors.log").open("a", encoding="utf-8", errors="replace") as fh:
            fh.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _step(n: int, title: str) -> None:
    bar = "─" * 56
    _log("")
    _log(bar)
    _log(f"▶ 步骤 {n}/{TOTAL_STEPS}　{title}")
    _log(bar)


def _pause_point() -> None:
    """安全点：允许按 P 暂停。暂停期间持续喂看门狗。"""
    if _PAUSE is not None:
        _PAUSE.check(_log, heartbeat=lambda: _beat("暂停等待中"))


def visible_sleep(seconds: float, reason: str) -> None:
    """长等待绝不沉默：每 10 秒报一次剩余时间（同时喂看门狗、响应暂停键）。"""
    if seconds < 12:
        time.sleep(seconds)
        return
    end = time.time() + seconds
    while True:
        remain = end - time.time()
        if remain <= 0:
            break
        time.sleep(min(10.0, remain))
        _log(f"    ⏳ {reason}，剩 {int(remain)} 秒…")
        _pause_point()


def sync(
    cfg: Config,
    *,
    state: State,
    only: list[str] | None = None,
    limit: int | None = None,
    refresh_followings: bool = False,
    interactive: bool = False,
    dry_run: bool = False,
    pause_enabled: bool = True,
) -> int:
    global _WD, _PAUSE
    started = time.time()

    _WD = Watchdog(cfg.scrape.watchdog_seconds)
    _WD.beat()
    _WD.start()
    _PAUSE = PauseController(enabled=pause_enabled)
    try:
        return _sync_inner(
            cfg, state=state, only=only, limit=limit,
            refresh_followings=refresh_followings,
            interactive=interactive, dry_run=dry_run,
            started=started,
        )
    finally:
        _WD.stop()
        _WD = None
        _PAUSE = None


def _sync_inner(
    cfg: Config,
    *,
    state: State,
    only, limit, refresh_followings, interactive, dry_run, started,
) -> int:
    ups_done = 0
    new_count = 0
    errors: list[dict] = []
    aborted = False

    # ---- 步骤 1：检测输出环境（不启动浏览器，纯文件/注册表检查，很快） ----
    _step(1, "检测 Obsidian 库与输出目录")
    status = detect_obsidian(cfg)
    for line in status.evidence:
        _log(f"· {line}")
    if status.usable:
        # 只是「本机有这个库」的提示；实际写到哪由下面 prepare_obsidian 决定
        _log(f"· 检测到本机 Obsidian 库：{status.vault_root}（仅提示，实际写入见下）")
    else:
        # 没装 Obsidian / 没建库都不影响：笔记就是普通 md 文件，目录会自动创建
        _log(f"· 未检测到可用的库（{status.why_not_usable()}），本次按 config.toml 的路径写 Markdown")

    # ---- 输出目录准备：缺失就整条建出来（父级全部补齐），建不出来立刻说清原因 ----
    notes_on = True
    output_errors: list[str] = []
    if notes_on:
        try:
            prepare_obsidian(cfg, log=_log)
            _log(f"· 笔记将写入：{cfg.vault.ups_dir}")
        except OutputError as exc:
            notes_on = False
            output_errors.append(f"Obsidian 笔记：{exc}")
            _log(f"✗ Obsidian 笔记目录准备失败：\n{exc}")
            raise

    if notes_on:
        # 目录整理（幂等、很快）：先把根目录散落的笔记收进 B站UP文件夹/，再按分区归位
        try:
            stray = [
                p for p in cfg.vault.up_dir.glob("*.md")
                if p.name != cfg.vault.index_note.name and note_mid(p)
            ]
            if stray:
                _log(f"· 发现 {len(stray)} 篇笔记还在根目录，正在收进 {cfg.vault.ups_subdir}/ …")
                migrate(cfg, state=state, rebuild_index=False, log=_log)
            else:
                zstats = organize_by_zone(cfg.vault.ups_dir, state, log=_log)
                if zstats["moved"] or zstats["renamed"]:
                    _log(f"· 已按分区归位 {zstats['moved'] + zstats['renamed']} 篇笔记")
        except Exception as exc:
            _log(f"[warn] 目录整理失败（不影响本次抓取）：{exc}")
    if _PAUSE is not None and _PAUSE.enabled:
        _log("· 运行中可随时按 P 暂停，再按 P（或 R）继续")
    covers_dir = cfg.vault.covers_dir

    # 缓存残缺（>= 上线前只读了一页的老数据）时必须重抓，否则会一直沿用错误数量
    incomplete = state.followings_incomplete()
    need_followings = refresh_followings or not state.followings or incomplete
    stale = state.followings_age_days() > cfg.scrape.refresh_followings_days

    headless = cfg.scrape.headless
    # 后台模式下不要为了「检查登录」就弹窗：先静默探测，只有真需要扫码才短暂开窗，
    # 扫完由 ensure_login_ready 立刻关掉；已有登录态时用户全程看不到窗口。
    if interactive and headless:
        ensure_login_ready(cfg, headless=True, log=_log)
    mode_txt = "有窗口（可实时观看）" if not headless else "无窗口"
    _step(2, f"检查登录态　[浏览器：{mode_txt}]")

    with browser_session(cfg, headless=headless) as ctx:
        info = nav_info(ctx)
        if not info.get("isLogin"):
            if not interactive:
                raise LoginRequired(
                    "登录态无效。请先双击 login.bat（或执行 `python BiliWatch_单文件版.py login`）扫码登录一次。"
                )
            info = ensure_login(ctx, interactive=True)
        _log(f"✓ 登录用户：{info.get('uname')}（UID {info.get('mid')}）")
        my_mid = info.get("mid") or ""

        page = ctx.new_page()
        # 预热一次首页：拿到 buvid3/ticket 等风控 cookie，空间页的空列表概率明显下降
        try:
            page.goto(HOME_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
            _log("✓ 首页预热完成（获取风控 cookie）")
        except Exception:
            _log("· 首页预热失败（不影响继续，仅风控概率略升）")

        # ---- 步骤 3：关注名单（followings.txt，一次抓取处处复用） ----
        _step(3, "关注名单（followings.txt）")
        txt_file = txt_path()
        have_txt = bool(load_txt())
        if need_followings or stale or not have_txt:
            if refresh_followings:
                reason = "手动指定 --refresh-followings"
            elif not have_txt:
                reason = f"{txt_file.name} 不存在或为空（首次运行会自动创建）"
            elif not state.followings or incomplete:
                reason = "本地缓存为空或残缺"
            else:
                reason = f"缓存已 {state.followings_age_days():.0f} 天（超过 {cfg.scrape.refresh_followings_days} 天，自动刷新）"
            _log(f"· 在线更新名单：{reason}")
            if incomplete and state.followings:
                _log(f"[fix] 缓存只有 {len(state.followings)} 个关注，与页面声明不符，重新抓取")
            try:
                items, declared = fetch_followings(page, my_mid, cfg, log=_log)
            except Exception as exc:
                # 超时/改版/风控都可能直接抛，一次异常不能打崩整轮：退到本地名单
                _log(f"[warn] 在线抓取名单失败（{type(exc).__name__}: {exc}），改用本地名单继续")
                _error_log(f"抓取关注名单异常：\n{traceback.format_exc()}")
                items, declared = [], 0
            if items:
                if declared and len(items) < declared:
                    # 本轮翻页失败抓少了：并入上次缓存的名单，尽量不让 TXT 缺人
                    merged = {u["mid"]: u for u in state.followings}
                    for u in items:
                        merged[u["mid"]] = u
                    _log(f"[fix] 本轮只抓到 {len(items)}/{declared} 个，与本地缓存合并后共 {len(merged)} 个")
                    items = list(merged.values())
                state.set_followings(items, declared)
                state.save()
                try:
                    save_txt(items)
                except OSError as exc:
                    _log(f"[warn] 名单 TXT 写入失败（不影响本轮抓取）：{exc}")
                _log(f"✓ 名单已更新并写入 {txt_file.name}：{len(items)} 个 UP")
            elif have_txt:
                _log("[warn] 在线抓取名单失败，沿用本地 TXT 名单")
            elif state.followings:
                _log("[warn] 在线抓取名单失败，沿用本地缓存")
        else:
            _log(f"✓ 从 {txt_file.name} 读取名单（缓存 {state.followings_age_days():.1f} 天，"
                 f"满 {cfg.scrape.refresh_followings_days} 天自动在线刷新；也可手动执行 python BiliWatch_单文件版.py followings）")

        # 名单来源优先级：TXT 文件 > 本地缓存（TXT 可手动编辑，UID 为准）
        txt_items = load_txt()
        if txt_items:
            targets = txt_items
            if not state.followings:
                state.set_followings(txt_items, declared=len(txt_items))
                state.save()
        else:
            targets = state.followings
        if only:
            wanted = {str(x) for x in only}
            targets = [u for u in targets if u["mid"] in wanted]
            missing = wanted - {u["mid"] for u in targets}
            targets += [{"mid": m, "uname": f"UP_{m}"} for m in sorted(missing)]
        if limit:
            targets = targets[:limit]
        if not targets:
            _log("没有可处理的 UP，退出（关注列表为空，可用 --refresh-followings 重新拉取）")
            return 0

        # ---- 步骤 4：并发抓取各 UP 的最新视频 ----
        w = max(1, cfg.scrape.workers)
        eta_min = len(targets) * 10 / 60 / w
        wtxt = f"{w} 个浏览器实例并发" if w > 1 else "单线程"
        _step(4, f"抓取各 UP 的最新视频（共 {len(targets)} 个，{wtxt}，预计 {eta_min:.0f}~{eta_min * 2:.0f} 分钟）")

        # 并发实例不能共用 .profile（有目录锁），导出登录态给它们共享
        cookies_path = cfg.profile_dir.parent / ".cookies.json"
        if not export_storage_state(ctx, cookies_path) and not cookies_path.exists():
            raise RuntimeError("登录态导出失败（.cookies.json 未生成），无法启动并发抓取")

        # 断点续跑：上一轮被看门狗强杀（exit 9）时，current_run 里留着进度，
        # 本轮直接从断点继续，不再从头重复抓已经写完的 UP。
        resume = state.begin_run()
        done_before: set[str] = set(resume.get("done", {}).keys()) if resume else set()
        skip_mids = {m for m, n in (resume.get("stuck", {}) or {}).items() if n >= 2} if resume else set()
        if resume:
            _log(f"[resume] 检测到 {resume['started_at']} 的未完成批次（已完成 {len(done_before)} 个），本次从断点继续")
            if skip_mids:
                names = "、".join(
                    next((u["uname"] for u in targets if u["mid"] == m), m) for m in skip_mids
                )
                _log(f"[resume] 以下 UP 连续卡死过，本轮跳过、下次整批运行时再试：{names}")

        taken = existing_note_map(cfg.vault.ups_dir, cfg.vault.up_dir) if notes_on else {}
        consecutive_fail = 0

        # 组装待抓队列：断点里已完成的直接记成功跳过
        jobs: list[dict] = []
        for idx, up in enumerate(targets, 1):
            mid, uname = up["mid"], up["uname"]
            prefix = f"({idx}/{len(targets)}) {uname}"
            if mid in done_before:
                _log(f"{prefix} —— ✓ 上一轮已完成，跳过")
                ups_done += 1
                continue
            if mid in skip_mids:
                _log(f"{prefix} —— [skip] 该 UP 曾连续卡死，本轮跳过（下次整批运行会自动重试）")
                continue
            jobs.append({
                "mid": mid,
                "uname": uname,
                # 缺分区的 UP 顺带补一次（worker 抓完视频后多打一个接口）
                "need_zone": not (state.up(mid) or {}).get("zone"),
            })
        # 注意：这里不再批量「认领」。批量认领会把 current_run.in_progress 覆盖成
        # 队列里最后一个 UP，导致「上次死在谁身上」永远判不准、卡死计数永不累加；
        # 改为 worker 真正开始抓某个 UP 时才认领（见 _on_start / on_start 回调）。
        state.save()  # 断点信息立刻落盘：被强杀后断点才准

        def _on_start(mid: str) -> None:
            """worker 真正开抓这个 UP 时回调：把「在办」标成它，供下次续跑判定卡死。"""
            try:
                if state.mark_in_progress(mid):
                    _log(f"   [warn] 上一轮就是卡在 {mid}，本次重试；再卡一次将自动跳过")
            except Exception:
                pass

        done_n = 0
        aborted_flag = {"v": False}

        def _circuit_break(reason: str) -> None:
            _log(f"[abort] {reason}，熔断收尾（已完成内容保留，断点已记录，下次运行从断点继续）")
            aborted_flag["v"] = True
            job_pool.abort.set()  # 剩余任务被 worker 快速跳过，结果很快收齐

        def _handle_result(mid: str, uname: str, result, error) -> None:
            nonlocal done_n, consecutive_fail, ups_done, new_count
            done_n += 1
            prefix = f"({done_n}/{len(jobs)}) {uname}"
            try:
                # ---- 失败：跳过并记录（错误日志独立成档，断点不标完成，下轮自动重试） ----
                if error is not None:
                    msg = f"{type(error).__name__}: {error}"
                    errors.append({"mid": mid, "uname": uname, "error": msg})
                    _log(f"{prefix} —— 失败：{msg}")
                    _error_log(f"{uname}（{mid}）：{msg}")
                    consecutive_fail += 1
                    if consecutive_fail >= MAX_CONSECUTIVE_FAILS:
                        _circuit_break(f"连续 {consecutive_fail} 个 UP 失败，疑似风控/改版")
                    return

                (scrape_result, zone_info) = result
                videos, avatar_path, _ = scrape_result
                if zone_info:
                    state.set_zone(mid, zone_info)
                if not videos:
                    # 关键：抓不到就什么都不写，绝不能用空列表覆盖掉已有的好笔记
                    _log(f"{prefix} —— 0 条视频（疑似风控/页面异常），保留原内容不动，下轮运行自动重试")
                    _error_log(f"{uname}（{mid}）：0 条视频（疑似风控/页面异常）")
                    consecutive_fail += 1
                    if consecutive_fail >= MAX_CONSECUTIVE_FAILS:
                        _circuit_break(f"连续 {consecutive_fail} 个 UP 抓不到数据，疑似风控/改版")
                    return
                consecutive_fail = 0

                fresh = state.record_videos(mid, uname, videos)
                entry = state.up(mid)
                fresh_bvs = {f["bv"] for f in fresh}

                # 封面下载（Obsidian 笔记内嵌入）
                cover_name: dict[str, str] = {}
                for v in videos:
                    _beat(f"下载封面 {v['bv']}（{uname}）")
                    dest = covers_dir / v["bv"]
                    saved = download_image(ctx, v.get("cover_url", ""), dest)
                    if saved:
                        # 只记文件名：封面按 BV 号命名、全库唯一，笔记挪到哪都不会指错
                        cover_name[v["bv"]] = saved.name
                    v["cover_path"] = str(saved) if saved else None

                # ---- 写这篇 UP 的 Markdown 笔记 ----
                if notes_on:
                    note_name = safe_filename(uname, mid, taken)
                    taken[note_name.lower()] = mid
                    entry["note_name"] = note_name

                    avatar_name = avatar_path.name if avatar_path else None
                    # 笔记落在「分区」子文件夹里：B站UP文件夹/科技/某UP.md
                    # 变量名不能叫 note_path：合并成单文件后 notes.note_path 会被改写为
                    # 裸名 note_path，与同名局部变量相撞 → UnboundLocalError
                    zone_for_path = entry.get("zone") or ""
                    target_note = note_path(cfg.vault.ups_dir, zone_for_path, note_name)
                    # 手写区可能还在老位置（分区子文件夹之前的两代结构），三处都看
                    manual = extract_manual(
                        read_note(target_note)
                        or read_note(cfg.vault.ups_dir / f"{note_name}.md")
                        or read_note(cfg.vault.up_dir / f"{note_name}.md")
                    )
                    content = render_up_note(
                        mid=mid,
                        uname=uname,
                        videos=videos,
                        entry=entry,
                        manual=manual,
                        cover_name_by_bv=cover_name,
                        avatar_name=avatar_name,
                        fresh_bvs=fresh_bvs,
                        updates_30d=state.recent_updates(mid),
                        zone_info=zone_info,
                    )
                    if not dry_run:
                        write_atomic(target_note, content)

                if dry_run:
                    planned = []
                    if notes_on:
                        planned.append(
                            "笔记 " + note_relpath(
                                cfg.vault.ups_subdir, entry.get("zone") or "", note_name
                            ) + ".md"
                        )
                    _log(f"{prefix} —— [dry-run] 将写入 {' + '.join(planned) or '无'}（新增 {len(fresh)} 条）")
                else:
                    _log(f"{prefix} —— ✓ {len(videos)} 条视频，新增 {len(fresh)} 条")

                # 每个 UP 处理完立刻落盘：即使中途被杀，进度也不丢（断点续传的根基）
                state.mark_done(mid)
                state.save()
                ups_done += 1
                new_count += len(fresh)
            except Exception as exc:  # 回调自身兜底：绝不让单个结果的处理崩掉主循环
                _error_log(f"{uname}（{mid}）：结果处理异常 {type(exc).__name__}: {exc}")
                _log(f"{prefix} —— [warn] 结果处理异常（不影响其他 UP）：{exc}")

        job_pool = WorkerPool(
            cfg,
            cookies_path=cookies_path,
            log=_log,
            on_result=_handle_result,
            is_paused=lambda: bool(_PAUSE is not None and _PAUSE.paused),
            tick=_pause_point,  # 主循环空闲间隙响应暂停键
            on_start=_on_start,  # 真正开抓时认领（卡死续跑判定依赖它）
        )
        if jobs:
            if not job_pool.run(jobs):
                aborted = True
            # 回调里触发的熔断不会体现在 run() 的返回值上（返回值只反映 pool 自身的
            # 熔断标志），必须把回调置的这个标志并进来，否则断了也会走 finish_run 清断点
            aborted = aborted or aborted_flag["v"]
        else:
            _log("· 待抓队列为空（全部已在断点中完成）")

        # ---- 步骤 5：输出 ----
        elapsed = time.time() - started
        run_record = {
            "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "mode": "试运行" if dry_run else "常规",
            "ups": ups_done,
            "new": new_count,
            "errors": errors,
            "duration": f"{elapsed / 60:.1f} 分钟",
        }

        _step(5, "更新 Obsidian 笔记与总览页")

        if dry_run:
            _log("[dry-run] 跳过文件写入")
        else:
            # ---- 5. Obsidian 笔记（总览页 + 分区笔记）----
            if notes_on:
                try:
                    rows = []
                    for mid, entry in state.data["ups"].items():
                        name = entry.get("note_name")
                        if not name:
                            continue
                        if not find_note(cfg.vault.ups_dir, name):
                            continue  # 笔记已被手动删除，就别在总览里留死链
                        rows.append(
                            {
                                "mid": mid,
                                "uname": entry.get("uname", ""),
                                "note_name": name,
                                "zone": entry.get("zone") or "",
                                "latest_pub": entry.get("latest_pub"),
                                "latest_title": entry.get("latest_title", ""),
                                "latest_url": entry.get("latest_url", ""),
                                "updates_30d": state.recent_updates(mid),
                            }
                        )
                    rows.sort(key=lambda r: (r["latest_pub"] or ""), reverse=True)
                    write_atomic(
                        cfg.vault.index_note,
                        render_index(
                            rows=rows,
                            last_run=run_record,
                            # 运行历史累积渲染：state.runs（历史）+ 本轮，最新在前
                            runs=[run_record] + (state.data.get("runs") or []),
                            ups_subdir=cfg.vault.ups_subdir,
                            favs_note="收藏夹" if (cfg.vault.up_dir / "收藏夹.md").exists() else None,
                        ),
                    )
                    # 分区笔记：UP 双链的唯一来源（总览只链分区，反向链接按分区隔离）
                    znotes = write_zone_notes(cfg, rows, log=_log)
                    _log(f"✓ 总览页已更新：{cfg.vault.index_note}"
                         f"（{len(rows)} 个 UP，链接指向 {cfg.vault.ups_subdir}/<分区>.md 分区笔记）")
                    _log(f"✓ 分区笔记已同步：{znotes} 篇（{cfg.vault.ups_subdir}/<分区>.md，收录该区全部 UP）")
                except OutputError as exc:
                    notes_on = False
                    output_errors.append(f"Obsidian 笔记：{exc}")
                    _log(f"✗ Obsidian 笔记写入失败：\n{exc}")
                except Exception as exc:  # 兜底：别让笔记的意外异常把整轮拖崩
                    notes_on = False
                    detail = f"{type(exc).__name__}: {exc}"
                    output_errors.append(f"Obsidian 笔记：{detail}")
                    _log(f"✗ Obsidian 笔记写入失败：{detail}")
                    _error_log(f"笔记导出异常：\n{traceback.format_exc()}")

            if output_errors:
                _log("[错误] 本次输出未全部成功，明细如下：")
                for e in output_errors:
                    _log(f"  · {e}")

        if not dry_run:
            state.add_run(run_record)
            if aborted:
                # 提前收尾（风控熔断/异常退出）：保留断点，下次运行从没跑完的地方继续
                state.save()
                _log("[resume] 本轮提前收尾，断点已保留；下次运行会自动从断点继续")
            else:
                state.finish_run()
            state.save()
            if state.last_save_error:
                _log(f"[warn] state.json 写入失败：{state.last_save_error}")
                _log("       本轮进度可能没保存（下次会重抓）；常见原因：文件被占用 / 磁盘只读或已满")

    if aborted:
        _log(f"本轮提前收尾：完成 {ups_done}/{len(targets)} 个 UP / 新增 {new_count} 条 / 失败 {len(errors)} 个 / 用时 {(time.time() - started) / 60:.1f} 分钟")
    else:
        _log(f"完成：{ups_done} 个 UP / 新增 {new_count} 条 / 失败 {len(errors)} 个 / 用时 {(time.time() - started) / 60:.1f} 分钟")
    if output_errors:
        _log(f"[错误] 有 {len(output_errors)} 项输出失败，详见上方明细（文件路径与原因）")
    return 1 if (aborted or output_errors) else 0

# ════════════════════════════════════════════════════════════════════
# 18 / 20 · cli —— 命令行入口：run / login / followings / favs / zones / migrate / schedule / doctor
#    （原文件：bilisync/cli.py）
# ════════════════════════════════════════════════════════════════════

"""命令行入口。

  python BiliWatch_单文件版.py run        正式抓取并写入 Obsidian
  python BiliWatch_单文件版.py login      扫码登录（保存登录态）
  python BiliWatch_单文件版.py migrate    整理目录：UP 笔记收进 B站UP文件夹/ 并修好链接
  python BiliWatch_单文件版.py schedule   安装/查看/删除 Windows 定时任务
  python BiliWatch_单文件版.py doctor     环境自检
"""
























TASK_PREFIX = "BiliWatch"


class _Tee:
    """把控制台输出同步写进日志文件。

    控制台有各种不可靠场景（快速编辑模式选中文本会阻塞 print、窗口被误关），
    有了文件日志，"卡在哪、死在哪"事后都能取证。
    """

    def __init__(self, console, file_fh):
        self.console = console
        self.file_fh = file_fh

    def write(self, s: str) -> int:
        try:
            self.file_fh.write(s)
            self.file_fh.flush()
        except Exception:
            pass
        try:
            return self.console.write(s)
        except UnicodeEncodeError:
            # 控制台是 GBK 时，✓ ▶ ─ 这类字符编不出来。绝不能因此把整行吞掉：
            # 先按控制台编码替换成 ?，再写一次。
            try:
                enc = getattr(self.console, "encoding", None) or "utf-8"
                self.console.write(s.encode(enc, "replace").decode(enc, "replace"))
            except Exception:
                pass
            return len(s)
        except Exception:
            return len(s)

    def reconfigure(self, **kwargs) -> None:
        """把 reconfigure 透传给真正的控制台流。

        日志接管发生在 main() 之前，此时 sys.stdout 已经是 _Tee；如果这里不转发，
        main() 里那句 reconfigure(errors="replace") 就落空，GBK 控制台遇到 ✓ 直接报错。
        """
        try:
            self.console.reconfigure(**kwargs)
        except Exception:
            pass

    def flush(self) -> None:
        for st in (self.console, self.file_fh):
            try:
                st.flush()
            except Exception:
                pass


def _log_dir() -> Path:
    """日志目录：优先 <数据目录>\\logs，不可写时退到临时目录（保证总能留下痕迹）。"""
    for cand in (PROJECT_ROOT / "logs", Path(tempfile.gettempdir()) / "BiliWatch-logs"):
        try:
            cand.mkdir(parents=True, exist_ok=True)
            return cand
        except Exception:
            continue
    return PROJECT_ROOT / "logs"


_LOG_FH = None            # 会话日志句柄（进程内唯一）
_LOG_PATH: Path | None = None
_BARE_RUN = False         # 本次是否「无参数」启动（= 双击/向导流程）


def _start_session_log(prefix: str = "session") -> Path | None:
    """进程一起来就接管 stdout/stderr，全部输出落进 logs\\<prefix>-时间戳.log。

    为什么要在最外层做：向导、doctor 自检、未捕获异常的堆栈，原本只存在于控制台。
    exe 双击运行时那个控制台是**进程自己的**，进程一退窗口立刻消失，用户什么都看不到。
    先落盘，才有事后取证的可能。
    """
    global _LOG_FH, _LOG_PATH
    if _LOG_FH is not None:
        return _LOG_PATH
    try:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = _log_dir() / f"{prefix}-{stamp}.log"
        fh = path.open("w", encoding="utf-8", errors="replace")
    except Exception:
        return None
    _LOG_FH, _LOG_PATH = fh, path
    sys.stdout = _Tee(sys.stdout, fh)
    sys.stderr = _Tee(sys.stderr, fh)
    return path


def _setup_run_log() -> None:
    """run 系列命令开始时确保日志已接管（入口通常已接管，这里只兜底）。"""
    _start_session_log("run")


def _publish_latest_log() -> None:
    """另存一份 latest.log：让用户（或我）不用翻时间戳就能找到「最近一次」。"""
    if not _LOG_PATH:
        return
    try:
        shutil.copyfile(_LOG_PATH, _LOG_PATH.with_name("latest.log"))
    except Exception:
        pass


_SHELL_IMAGES = {
    "cmd.exe", "powershell.exe", "pwsh.exe", "bash.exe", "sh.exe",
    "wt.exe", "windowsterminal.exe", "conhost.exe", "explorer.exe",
}


def _console_process_names() -> list[str]:
    """列出挂在当前控制台上的进程名（小写）。取不到的返回空串。"""
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.windll.kernel32
    pids = (ctypes.c_uint * 32)()
    n = k32.GetConsoleProcessList(pids, 32)
    names: list[str] = []
    for i in range(max(int(n), 0)):
        handle = k32.OpenProcess(0x1000, False, pids[i])   # QUERY_LIMITED_INFORMATION
        if not handle:
            names.append("")
            continue
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if k32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                names.append(os.path.basename(buf.value).lower())
            else:
                names.append("")
        finally:
            k32.CloseHandle(handle)
    return names


def _console_will_vanish() -> bool:
    """控制台窗口是否会随本进程一起消失 —— 也就是「双击 exe」这种场景。

    从 cmd / PowerShell / 批处理里启动时控制台属于 shell，进程退出后窗口还在，
    多按一次键纯属打扰；只有双击 exe 时窗口是程序自己的，一退就关。
    判断：控制台上挂着 cmd.exe / powershell.exe 之类的 shell 就说明窗口不是我们的。
    （不能简单用「进程数==1」：PyInstaller onefile 的引导进程和应用进程都挂着，
    真实双击时也永远是 2 个；也不能用 sys.stdin.isatty()，Windows 上 NUL 也算字符设备。）
    """
    if os.name != "nt":
        return False
    try:
        import ctypes

        k32 = ctypes.windll.kernel32
        if not k32.GetConsoleWindow():
            # 没有控制台：定时任务 / 服务 / IDE 里的管道 / 完全重定向
            return False
        names = _console_process_names()
        if names:
            return not any(n in _SHELL_IMAGES for n in names)
        pids = (ctypes.c_uint * 8)()
        return k32.GetConsoleProcessList(pids, 8) <= 1
    except Exception:
        try:
            return bool(sys.stdin and sys.stdin.isatty())
        except Exception:
            return False


def _dump_crash(exc_type, exc, tb) -> None:
    """未捕获异常：完整堆栈写独立文件，并尽量打到控制台（不依赖 tee 是否还活着）。"""
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    path = None
    try:
        path = _log_dir() / f"crash-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
        path.write_text(text, encoding="utf-8", errors="replace")
    except Exception:
        path = None
    for stream in (sys.stderr, sys.__stderr__):
        try:
            print("\n" + "=" * 64, file=stream)
            print("程序遇到未处理的错误，已中止。", file=stream)
            print(text, file=stream)
            if path:
                print(f"日志文件：{path}", file=stream)
            print("=" * 64, file=stream)
            stream.flush()
            break
        except Exception:
            continue


def _hold(tip: str) -> None:
    """真的把窗口停住。优先读控制台按键（msvcrt），stdin 被重定向也照样有效。

    只用 input() 不够：如果 stdin 不是当前控制台（比如从别的进程 start 出来、
    或被重定向），input() 会立刻 EOF，窗口照样一闪而过。
    """
    try:
        import msvcrt

        print(f"\n{tip} —— 按任意键关闭窗口…", flush=True)
        msvcrt.getch()
        return
    except (Exception, KeyboardInterrupt):
        pass
    try:
        input(f"\n{tip} —— 按回车键关闭窗口…")
    except (Exception, KeyboardInterrupt):
        pass


def _console_diag() -> str:
    """排查「窗口是否驻留」用的诊断串（BILIWATCH_DEBUG_HOLD=1 时打印）。"""
    try:
        import ctypes

        k32 = ctypes.windll.kernel32
        pids = (ctypes.c_uint * 8)()
        n = k32.GetConsoleProcessList(pids, 8)
        return (f"hwnd={k32.GetConsoleWindow()} n={n} "
                f"frozen={bool(getattr(sys, 'frozen', False))} stdin={sys.stdin!r}")
    except Exception as exc:
        return f"诊断失败：{exc}"


def _wait_exit(rc: int) -> None:
    """退出前停一下：双击 exe 时窗口属于进程，程序一退窗口立刻消失。

    规则：出错一律停（除 stdin 不可用）；成功时只在「向导流程」停，
    命令行带参数成功执行（如 Bili.exe run --limit 3）直接返回，不打扰。
    定时任务/静默运行可用环境变量 BILIWATCH_NO_HOLD=1 关掉。
    """
    _publish_latest_log()
    if _LOG_PATH:
        try:
            print(f"\n[日志] 本次运行完整记录：{_LOG_PATH}")
            print(f"[日志] 最近一次的副本：{_LOG_PATH.with_name('latest.log')}")
        except Exception:
            pass
    if os.environ.get("BILIWATCH_DEBUG_HOLD"):
        print(f"[debug] rc={rc} bare={_BARE_RUN} vanish={_console_will_vanish()} {_console_diag()}")
    if rc == 0 and not _BARE_RUN:
        return
    if os.environ.get("BILIWATCH_NO_HOLD") or not _console_will_vanish():
        return
    tip = ("程序已结束" if rc == 0
           else "程序出错了（把上面的报错或日志文件发给维护者即可定位）")
    _hold(tip)


def _run_guarded() -> int:
    """顶层保护壳：捕获一切异常 → 落日志 → 留住窗口 → 返回退出码。

    没有这层壳时，任何未捕获异常（含 SystemExit(字符串)）都会让 exe 一闪而过。
    """
    global _BARE_RUN
    rc = 0
    try:
        rc = _entry()          # noqa: F821 —— 由文件末尾的第 21 节定义
    except SystemExit as exc:
        code = exc.code
        if code is None:
            rc = 0
        elif isinstance(code, int):
            rc = code
        else:
            rc = 1
            if str(code).strip():
                try:
                    print(code)
                except Exception:
                    pass
    except KeyboardInterrupt:
        print("\n已中断（Ctrl+C）。")
        rc = 130
    except BaseException:
        _dump_crash(*sys.exc_info())
        rc = 1
    finally:
        try:
            _wait_exit(rc)
        except Exception:
            pass
    return rc


def _cfg(args) -> Config:
    return load_config(args.config)


# ---------------- run ----------------

def cmd_run(args) -> int:
    _setup_run_log()
    cfg = _cfg(args)
    # --show / --headless 覆盖配置文件里的 headless
    if getattr(args, "headless", False):
        cfg.scrape.headless = True
    if getattr(args, "headless", False):
        cfg.scrape.headless = True
    elif getattr(args, "show", False):
        cfg.scrape.headless = False
    state = State.load(STATE_FILE)
    only = [x.strip() for x in (args.only or "").split(",") if x.strip()]
    try:
        return sync(
            cfg,
            state=state,
            only=only or None,
            limit=args.limit,
            refresh_followings=args.refresh_followings,
            interactive=args.login,
            dry_run=args.dry_run,
            pause_enabled=not getattr(args, "no_pause", False),
        )
    except LoginRequired as exc:
        print(f"[登录] {exc}")
        return 2
    except RuntimeError as exc:
        # OutputError 也是 RuntimeError：目录不可写、文档被占用这类可预期问题
        # 只打一行明确原因，不吐一屏 traceback
        print(f"[错误] {exc}")
        return 1


# ---------------- migrate ----------------

def cmd_migrate(args) -> int:
    """把 UP 笔记按「分区 → UP」两级整理进 B站UP文件夹/，并修引用、重建总览。"""
    cfg = _cfg(args)
    state = State.load(STATE_FILE)
    print("== 目录整理 ==")
    stats = migrate(
        cfg,
        state=state,
        dry_run=args.dry_run,
        rebuild_index=not args.no_index,
    )
    if args.dry_run:
        print("\n（dry-run 未改动任何文件；去掉 --dry-run 才会真正执行）")
        return 0
    print(
        f"\n完成：搬入 {stats['moved']} 篇 / 改名 {stats['renamed']} 篇 / "
        f"按分区归位 {stats['zoned']} 篇 / 修图片引用 {stats['embeds']} 处"
    )
    print(f"当前结构：{cfg.vault.up_dir.name}/ ← 总览页；"
          f"{cfg.vault.ups_subdir}/<分区>/ ← 各分区的 UP 笔记")
    return 0


# ---------------- login ----------------

def cmd_login(args) -> int:
    cfg = _cfg(args)
    print("打开浏览器，请扫码登录…")
    with browser_session(cfg, headless=False) as ctx:
        info = ensure_login(ctx, interactive=True, wait_seconds=args.timeout)
    print(f"已保存登录态到：{cfg.profile_dir}")
    print(f"当前账号：{info.get('uname')}（UID {info.get('mid')}）")
    return 0


# ---------------- followings（独立功能：只抓关注名单） ----------------

def cmd_followings(args) -> int:
    """单独抓一次关注名单，写入 followings.txt（不抓视频、不写笔记）。

    用途：手动触发更新名单；正式抓取运行时若名单过期也会自动更新（自动方式）。
    """
    _setup_run_log()
    cfg = _cfg(args)









    print("== 抓取关注名单 ==")
    try:
        if not args.show:
            # 后台模式：已登录不弹窗；确实需要扫码才短暂开窗，扫完立即关闭
            ensure_login_ready(cfg, headless=True, log=print)
        with browser_session(cfg, headless=not args.show) as ctx:
            info = nav_info(ctx)
            if not info.get("isLogin"):
                info = ensure_login(ctx, interactive=True)
            my_mid = info.get("mid") or ""
            print(f"登录用户：{info.get('uname')}（UID {my_mid}）")

            page = ctx.new_page()
            try:
                page.goto(HOME_URL, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)
            except Exception:
                pass  # 预热失败不阻塞

            try:
                items, declared = fetch_followings(page, my_mid, cfg, log=print)
            except Exception as exc:
                print(f"[warn] 在线抓取名单失败：{type(exc).__name__}: {exc}")
                items, declared = [], 0
    except LoginRequired as exc:
        print(f"[登录] {exc}")
        return 2

    if not items:
        print("[warn] 没抓到任何关注（疑似风控或登录态异常），TXT 未改动")
        return 1
    state = State.load(STATE_FILE)
    state.set_followings(items, declared)
    state.save()
    try:
        txt = save_txt(items)
    except OSError as exc:
        print(f"[错误] 名单 TXT 写入失败：{exc}")
        return 1
    print(f"✓ 名单已写入：{txt}")
    print(f"✓ 共 {len(items)} 个关注"
          + ("（与页面声明一致）" if declared == len(items) else
             f"（页面声明 {declared} 个，建议稍后重跑一次）" if declared else ""))
    return 0


def cmd_favs(args) -> int:
    """单独抓一次 B 站收藏夹，写入「收藏夹.md」（不抓 UP 视频、不动总览排行）。"""
    _setup_run_log()
    cfg = _cfg(args)









    print("== 抓取收藏夹 ==")
    try:
        if not args.show:
            # 后台模式：已登录不弹窗；确实需要扫码才短暂开窗，扫完立即关闭
            ensure_login_ready(cfg, headless=True, log=print)
        with browser_session(cfg, headless=not args.show) as ctx:
            info = nav_info(ctx)
            if not info.get("isLogin"):
                info = ensure_login(ctx, interactive=True)
            # 预热一次首页，降低接口风控概率
            page = ctx.new_page()
            try:
                page.goto(HOME_URL, wait_until="domcontentloaded")
                page.wait_for_timeout(1200)
            except Exception:
                pass
            if args.folders_only:
                # 只列清单不抓内容：确认登录态/收藏夹结构用，几秒出结果
                list_folders(page, log=print)
            else:
                sync_favs(
                    cfg,
                    page,
                    state=State.load(STATE_FILE),
                    log=print,
                    refresh_zones=args.refresh_zones,
                    with_covers=not args.no_covers,
                )
    except LoginRequired as exc:
        print(f"[登录] {exc}")
        return 2
    except RuntimeError as exc:
        print(f"[错误] {exc}")
        return 1
    return 0


def cmd_zones(args) -> int:
    """为关注 UP 批量标注分区（B 站官方分区，取最新一稿所属分区）。

    - 数据源：UP 最新一稿 BV → /x/web-interface/view 的 tid → 内置官方分区表；
    - 已标注的 UP 默认跳过（--force 强制重抓），因此支持断点续跑；
    - 每个结果立即落盘 state.json 并原位补丁对应笔记（不整篇重写）；
    - 单个失败只记日志，不中断整批。
    """
    _setup_run_log()
    cfg = _cfg(args)









    state = State.load(STATE_FILE)
    targets = state.followings or []
    if args.only:
        want = {m.strip() for m in args.only.split(",")}
        targets = [u for u in targets if u["mid"] in want]
    skip = 0 if args.force else sum(1 for u in targets if (state.up(u["mid"]) or {}).get("zone"))
    todo = [u for u in targets if args.force or not (state.up(u["mid"]) or {}).get("zone")]
    print(f"== 分区标注 == 共 {len(targets)} 个 UP：待标注 {len(todo)}，已标注跳过 {skip}")

    if not todo:
        print("没有需要标注的 UP。")
        return 0

    try:
        if not args.show:
            # 后台模式：已登录不弹窗；确实需要扫码才短暂开窗，扫完立即关闭
            ensure_login_ready(cfg, headless=True, log=print)
        with browser_session(cfg, headless=not args.show) as ctx:
            info = nav_info(ctx)
            if not info.get("isLogin"):
                info = ensure_login(ctx, interactive=True)
            page = ctx.new_page()
            try:
                page.goto(HOME_URL, wait_until="domcontentloaded")
                page.wait_for_timeout(1200)
            except Exception:
                pass
            import random
            ok = fail = 0
            for i, u in enumerate(todo, 1):
                mid, uname = u["mid"], u["uname"]
                entry = state.up(mid) or {}
                # 取 history 里最新发布的一稿 BV
                hist = sorted(entry.get("history") or [], key=lambda h: h.get("pub") or "", reverse=True)
                bv = hist[0]["bv"] if hist else ""
                info_z = fetch_up_zone(page, bv, mid=mid, log=print)
                if info_z:
                    state.set_zone(mid, info_z)
                    state.save()  # 逐个落盘：中断后续跑自动跳过已完成的
                    # 原位补丁笔记（找不到笔记文件就只存 state，下次运行重写笔记时自动带上）
                    name = entry.get("note_name")
                    if name:
                        p = find_note(cfg.vault.ups_dir, name)
                        if p:
                            patch_zone(p, info_z)
                    print(f"({i}/{len(todo)}) {uname} —— ✓ {describe_zone(info_z)}")
                    ok += 1
                else:
                    print(f"({i}/{len(todo)}) {uname} —— 未取到（无稿件/接口失败/新分区，下轮重试）")
                    fail += 1
                time.sleep(random.uniform(0.6, 1.4))
    except LoginRequired as exc:
        print(f"[登录] {exc}")
        return 2
    except RuntimeError as exc:
        print(f"[错误] {exc}")
        return 1

    print(f"完成：成功 {ok} / 失败 {fail}（失败的下次重跑本命令即可续跑）")

    # 分区可能变了：把笔记挪到新的分区文件夹，并重建总览的链接（幂等）
    if ok:
        stats = migrate(cfg, state=state, log=print)
        if stats["zoned"]:
            print(f"✓ 已按分区归位 {stats['zoned']} 篇笔记")
    return 0


# ---------------- schedule ----------------

def _task_name(index: int) -> str:
    return TASK_PREFIX if index == 1 else f"{TASK_PREFIX}-{index}"


def _run_command() -> str:
    """定时任务走 run-silent.bat：不弹窗、日志进 logs\run.log。"""
    bat = PROJECT_ROOT / "run-silent.bat"
    return f'"{bat}"'


def cmd_schedule(args) -> int:
    if platform.system() != "Windows":
        print("schedule 命令目前只支持 Windows（用 schtasks）。其他系统请用 cron 调用 run.bat。")
        return 1

    if args.action == "status":
        out = subprocess.run(["schtasks", "/Query", "/FO", "LIST"], capture_output=True, text=True, encoding="gbk", errors="replace")
        blocks = [b for b in out.stdout.split("\n\n") if TASK_PREFIX in b]
        if not blocks:
            print("尚未安装任何定时任务。")
        for b in blocks:
            keep = [ln for ln in b.splitlines() if any(k in ln for k in ("TaskName", "任务名", "Next Run", "下次运行", "Status", "状态", "Start", "开始"))]
            print("\n".join(keep))
            print("-" * 40)
        return 0

    if args.action == "remove":
        for i in range(1, 9):
            subprocess.run(["schtasks", "/Delete", "/TN", _task_name(i), "/F"], capture_output=True)
        print("已删除所有 BiliWatch 定时任务。")
        return 0

    # install
    times = [t.strip() for t in (args.at or ",".join(_cfg(args).schedule_times)).split(",") if t.strip()]
    for t in times:
        if not (len(t) == 5 and t[2] == ":" and t[:2].isdigit() and t[3:].isdigit()):
            print(f"时间格式不对：{t}，应为 HH:MM")
            return 1

    for i, t in enumerate(times, 1):
        subprocess.run(["schtasks", "/Delete", "/TN", _task_name(i), "/F"], capture_output=True)
        cmd = [
            "schtasks", "/Create",
            "/TN", _task_name(i),
            "/TR", _run_command(),
            "/SC", "DAILY",
            "/ST", t,
            "/F",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="gbk", errors="replace")
        if res.returncode == 0:
            print(f"✓ 已创建 {_task_name(i)}：每天 {t}")
        else:
            detail = (res.stderr or res.stdout).strip()
            print(f"✗ 创建 {_task_name(i)} 失败：{detail}")
            print(
                "\n可以手动兜底：打开「任务计划程序」→ 创建基本任务 → 每天 → "
                f'操作选「启动程序」，程序填：{PROJECT_ROOT / "run-silent.bat"}'
            )
            return 1

    print("\n提示：任务在已登录的当前 Windows 用户下运行；到点会后台执行 run.bat，日志追加到 logs\\run.log")
    print("撤销：python BiliWatch_单文件版.py schedule remove")
    return 0


# ---------------- doctor ----------------

def cmd_doctor(args) -> int:
    """环境自检。返回码：0=通过；2=可继续（只有登录态这类「开跑时会自愈」的问题）；1=有问题。

    分开的理由：向导第 2 步原本只要 doctor 非 0 就整体中止，导致新电脑上
    「未登录」这种完全正常的初始状态被当成致命错误，直接退出。
    """
    bad: list[str] = []    # 硬失败：不处理就跑不起来
    soft: list[str] = []   # 软问题：可继续（开跑时会自动扫码 / 自动补目录）
    print("== 环境自检 ==")

    cfg = None
    try:
        cfg = load_config(args.config)
        print(f"✓ 配置加载成功：{args.config or 'config.toml'}")
    except Exception as exc:
        bad.append("配置加载失败")
        print(f"✗ 配置加载失败：{exc}")

    if cfg:
        for label, path in [
            ("库根目录", cfg.vault.root),
            ("笔记根目录", cfg.vault.notes_root),
        ]:
            if Path(path).exists():
                print(f"✓ {label}存在：{path}")
            else:
                # 不存在不算失败：运行时会自动补齐全部父级目录（见 prepare_obsidian）
                print(f"· {label}暂不存在，运行时自动创建：{path}")
        print(f"· B站分区目录：{cfg.vault.up_dir}")
        print(f"· UP 笔记目录：{cfg.vault.ups_dir}（每个 UP 一篇）")
        print(f"· 总览页：{cfg.vault.index_note}")

        # 输出自检：不再要求装 Obsidian，只校验「目录能不能建、能不能写」
        st = detect_obsidian(cfg)
        for line in st.evidence:
            print(f"· {line}")
        if st.usable:
            print(f"· 检测到本机 Obsidian 库：{st.vault_root}（仅提示；实际写入路径见下）")
        else:
            print(f"· 未检测到可用的库（{st.why_not_usable()}），仍按 config.toml 的路径写 Markdown")

        # 用运行时同样的规则算出「实际会写到哪」，配置里的路径失效也能预测到兜底位置
        try:
            root, detail = plan_obsidian(cfg)
        except OutputError as exc:
            bad.append("笔记目录不可用")
            print(f"✗ 笔记目录不可用：\n{exc}")
        else:
            if root != cfg.vault.notes_root:
                print(f"· [warn] 配置里的笔记目录不可用，运行时会自动改用：{root}")
                retarget_vault(cfg, root)
            print(f"· 笔记将写入：{cfg.vault.ups_dir}")
            print(f"✓ 笔记目录可写：{detail}")

    try:
        from playwright.sync_api import sync_playwright  # noqa: F401

        print("✓ Playwright 已安装")
    except ImportError:
        bad.append("缺少 playwright")
        print("✗ Playwright 未安装：python -m pip install playwright")

    if cfg:
        try:
            with browser_session(cfg, headless=True) as ctx:
                info = nav_info(ctx)
                if info.get("isLogin"):
                    print(f"✓ 登录态有效：{info.get('uname')}（UID {info.get('mid')}）")
                else:
                    # 未登录不是故障：新电脑必然没登录态，第 4 步开跑时会自动弹二维码
                    soft.append("未登录")
                    print("! 登录态无效或已过期：不用现在处理，第 4 步开跑时会自动弹二维码窗口")
                    print("  （想先单独登录也可以：命令行执行 login）")
        except Exception as exc:
            bad.append("浏览器启动失败")
            print(f"✗ 浏览器启动失败：{exc}")
            print("  常见原因：Chromium 内核未下载完成 / 被杀毒软件拦截 / 磁盘空间不足")
            print("  手动补装：在命令行执行  Bili.exe login  （会自动重试下载内核）")

        st = State.load(STATE_FILE)
        print(f"· 关注列表缓存：{len(st.followings)} 个 UP（{st.data['followings'].get('refreshed_at') or '未抓取'}）")
        print(f"· 已记录 UP：{len(st.data['ups'])} 个")

    if bad:
        print("\n整体：未通过 —— 上面打了 ✗ 的项目必须先处理（共 %d 项）" % len(bad))
        return 1
    if soft:
        print("\n整体：可继续 —— 只有「%s」这一项，开跑时会自动处理，不是错误" % "、".join(soft))
        return 2
    print("\n整体：通过")
    return 0


# ---------------- 入口 ----------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="BiliWatch", description="B站关注 UP 更新 → Obsidian")
    p.add_argument("--config", help="配置文件路径（默认 config.toml）")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="抓取并写入笔记")
    r.add_argument("--only", help="只处理指定 mid，逗号分隔")
    r.add_argument("--limit", type=int, help="只处理前 N 个 UP（调试用）")
    r.add_argument("--refresh-followings", action="store_true", help="强制重新抓取关注列表")
    r.add_argument("--login", action="store_true", help="未登录时弹窗扫码")
    r.add_argument("--show", action="store_true", help="显示浏览器窗口，实时观看抓取过程（run.bat 默认带此参数）")
    r.add_argument("--headless", action="store_true", help="强制无窗口（定时任务/后台跑时用）")
    r.add_argument("--no-pause", action="store_true", help="禁用运行中的按 P 暂停功能")
    r.add_argument("--dry-run", action="store_true", help="只打印不写文件")
    r.set_defaults(func=cmd_run)

    lg = sub.add_parser("login", help="扫码登录并保存登录态")
    lg.add_argument("--timeout", type=int, default=300, help="等待登录的秒数")
    lg.set_defaults(func=cmd_login)

    fw = sub.add_parser("followings", help="只抓关注名单到 followings.txt（不抓视频）")
    fw.add_argument("--show", action="store_true", help="显示浏览器窗口")
    fw.set_defaults(func=cmd_followings)

    fv = sub.add_parser("favs", help="抓取我的 B 站收藏夹到「收藏夹.md」")
    fv.add_argument("--show", action="store_true", help="显示浏览器窗口")
    fv.add_argument("--headless", action="store_true", help="后台运行（默认即是，供一键运行统一传参）")
    fv.add_argument("--no-covers", action="store_true", help="不下载封面缩略图（只写文字列表）")
    fv.add_argument("--refresh-zones", action="store_true", help="忽略缓存，重新解析每个 UP 的分区")
    fv.add_argument("--folders-only", action="store_true", help="只获取收藏夹清单（名称/条数），不抓视频不写笔记")
    fv.set_defaults(func=cmd_favs)

    zn = sub.add_parser("zones", help="为关注 UP 批量标注分区（写入 state + 笔记）")
    zn.add_argument("--show", action="store_true", help="显示浏览器窗口")
    zn.add_argument("--force", action="store_true", help="已标注过的也重新抓（默认跳过）")
    zn.add_argument("--only", help="只处理指定 mid（逗号分隔）")
    zn.set_defaults(func=cmd_zones)

    mg = sub.add_parser("migrate", help="把 UP 笔记收进子文件夹并修好图片/链接引用")
    mg.add_argument("--dry-run", action="store_true", help="只打印计划，不动文件")
    mg.add_argument("--no-index", action="store_true", help="不重建总览页（只搬文件）")
    mg.set_defaults(func=cmd_migrate)

    sc = sub.add_parser("schedule", help="Windows 定时任务管理")
    sc.add_argument("action", choices=["install", "remove", "status"])
    sc.add_argument("--at", help="执行时刻，逗号分隔，如 09:00,21:00")
    sc.set_defaults(func=cmd_schedule)

    d = sub.add_parser("doctor", help="环境自检")
    d.set_defaults(func=cmd_doctor)
    return p


_RULE = "─" * 60


def _prog() -> str:
    """当前程序的自称：打包后是 Bili.exe，源码运行是 python xxx.py。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).name
    return "python BiliWatch_单文件版.py"


def _ask(prompt: str, allowed: dict[str, str], default: str | None = None) -> str:
    """循环询问直到拿到合法选项；直接回车用 default（None 表示必须明确选）。"""
    while True:
        raw = input(prompt).strip()
        if not raw and default is not None:
            return default
        if raw in allowed:
            return raw
        print("  输入无效，请重新选择：" + "  ".join(f"[{k}] {v}" for k, v in allowed.items()))


def _confirm(prompt: str, default: str = "1") -> bool:
    return _ask(prompt, {"1": "继续", "2": "退出"}, default) == "1"


def _banner(step: int, title: str, desc: str = "") -> None:
    print()
    print("   " + _RULE)
    print(f"   步骤 {step}/4  ·  {title}")
    if desc:
        print(f"   {desc}")
    print("   " + _RULE)
    print()


def _wizard() -> list[list[str]]:
    """4 步交互向导：运行设置 → 环境自检 → 扫码登录 → 选任务执行。

    原来这套流程在「一键运行.bat」里，但只拷 exe 到别的电脑就没有 bat 了，
    所以内置进程序本身。返回要依次执行的命令序列；中途退出返回空列表。
    输入流不可用（EOF）时抛 EOFError，由 main() 兜底成 run。
    """
    print("=" * 60)
    print("     B 站 UP 更新监控  ·  一键运行（分步交互版）")
    print("=" * 60)
    print()
    print("  流程共 4 步，每步开始前都会暂停让你确认；")
    print("     输入 [1] 继续本步，[2] 退出脚本。")
    print("     输出固定为 Obsidian Markdown 笔记；第 1 步只选浏览器方式，")
    print("     第 4 步选任务：关注UP / 我的收藏夹 / 收藏夹列表。")

    # ---------- 步骤 1：运行设置 ----------
    _banner(1, "运行设置", "选择浏览器运行方式（输出固定为 Obsidian Markdown 笔记）")
    print("  浏览器模式")
    print("   [1] 前台运行 — 弹出浏览器窗口，能看见每个 UP 的页面在翻")
    print("                  适用：第一次用、想确认程序真在干活、排查抓不到数据")
    print("                  代价：多占 1~2 GB 内存，窗口会挡住屏幕")
    print("   [2] 后台运行 — 不弹窗口，只看控制台文字进度")
    print("                  适用：长时间挂机、离开电脑、远程或定时执行")
    print("                  代价：出问题只能靠日志定位（logs\\ 目录）")
    print()
    bm = _ask("请选择浏览器模式  [1] 前台 / [2] 后台 ：", {"1": "前台", "2": "后台"}, "2")

    run_flags = ["--show"] if bm == "1" else ["--headless"]
    bm_cn = "前台运行（显示浏览器窗口）" if bm == "1" else "后台运行（不显示浏览器窗口）"

    print()
    print(f"   {_RULE}")
    print(f"   本次设置：浏览器 = {bm_cn}")
    print("             输出到 = Obsidian Markdown（每个 UP 一篇 md + 总览页 + 收藏夹.md）")
    print("             结果目录：08_B站关注\\B站UP文件夹\\ 与 B站关注总览.md")
    print(f"   等价命令：{_prog()} run {' '.join(run_flags)}")
    print(f"   {_RULE}")
    if not _confirm("[1] 按此设置继续  [2] 退出："):
        return []

    # ---------- 步骤 2：环境自检 ----------
    _banner(2, "环境自检", "检查配置 / 库路径 / 依赖 / 登录态，并校验笔记目录可写性（约 10~20 秒）")
    if not _confirm("[1] 开始自检  [2] 退出："):
        return []
    print("\n   >> 正在执行环境自检…")
    while True:
        dargs = build_parser().parse_args(["doctor"])
        rc = dargs.func(dargs) or 0
        if rc == 0:
            print("   √ 步骤 2/4 完成：自检通过")
            break
        if rc == 2:
            # 只有「未登录」这类可自愈项：不拦，第 4 步会弹二维码
            print("   ! 自检没有发现故障项（未登录属正常，开跑时会自动扫码），继续下一步。")
            break
        # rc == 1：确实有问题。不直接退出 —— 给重试机会，并把日志位置摆出来
        print("\n   × 自检未通过：上面打 ✗ 的项目要先处理")
        print("     常见原因：输出目录不可写（OneDrive/受控文件夹访问）、配置里的路径是老机器的、"
              "Chromium 没下完、被杀毒软件拦截")
        if _LOG_PATH:
            print(f"     本次完整日志：{_LOG_PATH}")
        choice = _ask(
            "[1] 处理完再自检一次  [2] 仍然继续（不推荐）  [3] 退出 ：",
            {"1": "重新自检", "2": "继续", "3": "退出"},
            "1",
        )
        if choice == "1":
            print("\n   >> 重新自检…")
            continue
        if choice == "2":
            print("   · 已跳过自检继续；如果开跑就报错，请把上面的日志发出来。")
            break
        return []

    # ---------- 步骤 3：扫码登录 ----------
    _banner(3, "扫码登录", "登录态有效则自动跳过；只有失效时才弹二维码窗口，扫完自动关闭")
    print("   · 本步不需要你操作：第 4 步开跑时会先静默检查登录态，")
    print("     已登录直接开始抓取；未登录才弹出二维码窗口，扫码后继续。")

    # ---------- 步骤 4：选任务并执行 ----------
    _banner(4, "选择任务并执行", f"先选本次任务范围，确认后开跑（{bm_cn}）")
    print("  任务范围")
    print("   [1] 全部（推荐）    — 关注 UP 更新 + 我的收藏夹，一次跑完")
    print("   [2] 仅关注 UP      — 只抓关注 UP 的最新投稿，收藏夹不动")
    print("   [3] 我的收藏夹      — 抓收藏视频写入 收藏夹.md（含封面、分区、UP 双链）")
    print("   [4] 收藏夹列表      — 只列出有哪些收藏夹、各多少条，不抓内容（几秒钟）")
    print()
    task = _ask(
        "请选择任务  [1] 全部 / [2] 仅UP / [3] 收藏夹 / [4] 列表 ：",
        {"1": "全部", "2": "仅UP", "3": "收藏夹", "4": "列表"},
        "1",
    )

    run_cmd = ["run", "--login", *run_flags]
    plan = {
        "1": [run_cmd, ["favs", *run_flags]],
        "2": [run_cmd],
        "3": [["favs", *run_flags]],
        "4": [["favs", "--folders-only", *run_flags]],
    }[task]
    what = {"1": "关注 UP 更新 + 我的收藏夹", "2": "仅关注 UP", "3": "我的收藏夹", "4": "收藏夹列表"}[task]
    print()
    equiv = " ; ".join(f"{_prog()} {' '.join(c)}" for c in plan)
    print(f"   即将执行：{what}")
    print(f"   等价命令：{equiv}")
    print()
    return plan


def _pid_alive(pid: int) -> bool:
    """判断进程是否还活着（不能用 os.kill(pid, 0)：Windows 上它会真去结束进程）。"""
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    try:
        import ctypes

        k32 = ctypes.windll.kernel32
        handle = k32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if not handle:
            return False
        try:
            return k32.WaitForSingleObject(handle, 0) == 0x102  # WAIT_TIMEOUT = 还在跑
        finally:
            k32.CloseHandle(handle)
    except Exception:
        return False


class _InstanceLock:
    """数据目录级单实例锁：防止两个实例互杀浏览器、互相覆盖 state.json。"""

    def __init__(self, path: Path):
        self.path = path

    def release(self) -> None:
        try:
            info = json.loads(self.path.read_text(encoding="utf-8") or "{}")
            if int(info.get("pid") or 0) == os.getpid():
                self.path.unlink()
        except Exception:
            pass


def _grab_instance_lock() -> _InstanceLock | None:
    """拿到锁返回对象；已有存活实例返回 None（调用方应退出）。"""
    p = STATE_FILE.parent / ".instance.lock"
    try:
        if p.exists():
            info = json.loads(p.read_text(encoding="utf-8") or "{}")
            pid = int(info.get("pid") or 0)
            if pid and pid != os.getpid() and _pid_alive(pid):
                print(f"[错误] 已有一个实例在运行（PID {pid}，启动于 {info.get('at') or '未知'}）")
                print("       两个实例同时跑会互相杀掉对方的浏览器，并互相覆盖 state.json。")
                print(f"       确认那个进程已退出的话，删除该文件后重试：{p}")
                print("       确实要并行：先设环境变量 BILIWATCH_ALLOW_MULTI=1")
                return None
    except Exception:
        pass  # 锁文件损坏/读不了：按无锁处理，别把人挡在外面
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps({"pid": os.getpid(), "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}),
            encoding="utf-8",
        )
    except OSError:
        pass  # 写不了锁就退化成无锁，不因此拦住用户
    return _InstanceLock(p)


_LOCK_CMDS = ("cmd_run", "cmd_favs", "cmd_zones")


def _run_with_lock(func, args) -> int:
    if getattr(func, "__name__", "") not in _LOCK_CMDS or os.environ.get("BILIWATCH_ALLOW_MULTI"):
        return func(args) or 0
    lock = _grab_instance_lock()
    if lock is None:
        return 3
    try:
        return func(args) or 0
    finally:
        lock.release()


def main(argv: list[str] | None = None) -> int:
    global _BARE_RUN
    _start_session_log()
    # 打包成 exe（PyInstaller）后，playwright 的 driver 目录里会有个 .local-browsers
    # 空壳目录，让它误以为浏览器内置在包里。frozen 时【无条件】指向系统浏览器缓存目录：
    # 目录不存在也要指过去 —— 那样 playwright 才知道该往哪下（缺失时自动下载）。
    if getattr(sys, "frozen", False):
        _base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.path.join(_base, "ms-playwright"))
    # 打包成 exe / 输出被重定向时，stdout 可能回退到 GBK 编码，
    # 遇到 ✓✗·—— 等符号会直接 UnicodeEncodeError 崩掉。改成替换不崩。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(errors="replace")
        except Exception:
            pass
    raw = list(sys.argv[1:] if argv is None else argv)
    if not raw:
        _BARE_RUN = True
        # 裸运行（双击 .py / 双击 exe / PyCharm / 不给子命令）：弹任务菜单让你选；
        # 只有输入流真的不可用（定时任务把 stdin 关了）才直接等价于 `run --login`。
        try:
            plan = _wizard()
        except EOFError:
            print("（检测到无交互输入，直接执行默认任务：run）\n")
            plan = [["run", "--login"]]
        except KeyboardInterrupt:
            print("\n已取消。")
            return 130
        if not plan:
            print("已退出。")
            return 0
        rc = 0
        for i, cmd in enumerate(plan, 1):
            if len(plan) > 1:
                print(f"—— 任务 {i}/{len(plan)}：bilisync {' '.join(cmd)} ——\n")
            args = build_parser().parse_args(cmd)
            rc = _run_with_lock(args.func, args)
            if rc != 0:
                print(f"\n[失败] 任务 {i}/{len(plan)} 退出码 {rc}，后续任务不再执行。")
                return rc
        return rc
    args = build_parser().parse_args(raw)
    return _run_with_lock(args.func, args)

# ════════════════════════════════════════════════════════════════════
# 19 / 20 · probe —— 页面结构探针（开发调试用，不参与日常流程）
#    （原文件：bilisync/probe.py）
# ════════════════════════════════════════════════════════════════════

"""一次性的页面结构探针：把真实 DOM 打出来，用来确认选择器而不是靠猜。

用法：把文件末尾的入口临时改成 probe_main("<url>") 再运行，或在 REPL 里调用
"""







PROBE_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

DUMP_JS = r"""
() => {
  const anchors = [...document.querySelectorAll('a[href*="/video/BV"]')];
  const out = [];
  for (const a of anchors.slice(0, 4)) {
    let box = a;
    for (let i = 0; i < 4 && box.parentElement; i++) box = box.parentElement;
    const img = box.querySelector('img');
    out.push({
      a_html: a.outerHTML.slice(0, 400),
      box_cls: box.className,
      box_text: (box.innerText || '').replace(/\n/g, ' | ').slice(0, 300),
      img_src: img ? img.src : null,
      img_attrs: img ? [...img.attributes].map(x => x.name + '=' + x.value.slice(0, 80)) : [],
      a_title: a.getAttribute('title'),
      a_text: (a.innerText || '').trim().slice(0, 120),
    });
  }
  return {
    url: location.href,
    title: document.title,
    count: anchors.length,
    body_head: document.body.innerText.slice(0, 600),
    samples: out,
  };
}
"""


def probe_main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "https://space.bilibili.com/546195/upload/video"
    with _sync_playwright()() as pw:
        browser = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(user_agent=PROBE_UA, locale="zh-CN", viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(5000)
        for _ in range(3):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(1200)
        data = page.evaluate(DUMP_JS)
        print("URL   :", data["url"])
        print("TITLE :", data["title"])
        print("COUNT :", data["count"])
        print("BODY  :", data["body_head"].replace("\n", " / ")[:500])
        for i, s in enumerate(data["samples"], 1):
            print(f"\n--- sample {i} ---")
            print("A_HTML:", s["a_html"])
            print("A_TITLE:", s["a_title"], "| A_TEXT:", s["a_text"])
            print("BOX_CLS:", s["box_cls"])
            print("BOX_TEXT:", s["box_text"])
            print("IMG:", s["img_src"])
            print("IMG_ATTRS:", s["img_attrs"])
        browser.close()
    return 0

# ════════════════════════════════════════════════════════════════════
# 20 / 20 · 入口 —— 程序入口：准备数据目录 → 交给命令行
#    （原文件：bilisync/__main__.py）
# ════════════════════════════════════════════════════════════════════


def _entry(argv: list[str] | None = None) -> int:
    """程序入口：接管日志 → 准备运行时目录 → 交给命令行解析。"""
    # 第一件事就把 stdout/stderr 复制进 logs\，这样向导、自检、
    # 乃至任何崩溃堆栈都能事后翻看（exe 的窗口会随进程一起消失）
    _start_session_log()
    if _LOG_PATH:
        print(f"[日志] 本次运行记录：{_LOG_PATH}")
    _write_default_config(PROJECT_ROOT)
    _ensure_silent_bat(PROJECT_ROOT)
    args = list(sys.argv[1:] if argv is None else argv)
    # 不传参数时不再强制打印帮助：交给 main() 决定（默认执行 run --login）
    return main(args)


if __name__ == "__main__":
    # _run_guarded 是顶层保护壳：任何未捕获异常都写日志 + 停住窗口，不再闪退
    sys.exit(_run_guarded())

