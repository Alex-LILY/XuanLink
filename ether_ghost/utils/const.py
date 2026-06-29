import os
import subprocess
from pathlib import Path


APP_VERSION = "0.2.5"
SETTINGS_VERSION = "0.0.1"
DB_FILENAME = "store.db"


def _is_wsl() -> bool:
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except Exception:
        return False


def _wsl_windows_appdata() -> "Path | None":
    """在 WSL 中调用 cmd.exe 获取 Windows 的 APPDATA 路径并转换为 WSL 路径。"""
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", "echo %APPDATA%"],
            capture_output=True, text=True, timeout=3
        )
        appdata = result.stdout.strip()
        if appdata and len(appdata) > 2 and appdata[1] == ":":
            drive = appdata[0].lower()
            rest = appdata[3:].replace("\\", "/")
            return Path(f"/mnt/{drive}/{rest}/ShadowHalberd")
    except Exception:
        pass
    return None


# 数据目录：优先使用环境变量，其次自动检测，最后按系统默认
if os.environ.get("SHADOWHALBERD_DATA"):
    DATA_FOLDER = Path(os.environ["SHADOWHALBERD_DATA"])
elif os.name == "posix" and _is_wsl():
    _wsl_path = _wsl_windows_appdata()
    DATA_FOLDER = _wsl_path if _wsl_path else Path("~/.local/share/ShadowHalberd").expanduser()
elif os.name == "posix":
    DATA_FOLDER = Path("~/.local/share/ShadowHalberd").expanduser()
elif os.name == "nt":
    DATA_FOLDER = Path("~/AppData/Roaming/ShadowHalberd").expanduser()
elif os.name == "darwin":
    DATA_FOLDER = Path("~/Library/Application Support/ShadowHalberd").expanduser()
else:
    DATA_FOLDER = Path(os.path.abspath("."))

DATA_FOLDER.mkdir(parents=True, exist_ok=True)

ANTSWORD_ENCODER_FOLDER = DATA_FOLDER / "AntSwordEncoder"

if not ANTSWORD_ENCODER_FOLDER.exists():
    ANTSWORD_ENCODER_FOLDER.mkdir()

    (ANTSWORD_ENCODER_FOLDER / "example-base64.js").write_text(
        """
module.exports = (pwd, data, ext={}) => {
    let randomID = `_0x${Math.random().toString(16).substr(2)}`;
    data[randomID] = Buffer.from(data['_']).toString('base64');
    data[pwd] = `eval(base64_decode($_POST[${randomID}]));`;
    delete data['_'];
    return data;
}
"""
    )

ANTSWORD_DECODER_FOLDER = DATA_FOLDER / "AntSwordDecoder"
ANTSWORD_DECODER_FOLDER.mkdir(exist_ok=True)


STORE_URL = "sqlite:///" + (DATA_FOLDER / DB_FILENAME).as_posix()
