import logging
import sys
from datetime import datetime

import structlog
from colorama import Fore, Style, init as colorama_init

colorama_init()


class ColoredConsoleRenderer:
    """简易彩色日志渲染器"""

    LEVEL_COLORS = {
        "debug": Fore.CYAN,
        "info": Fore.GREEN,
        "warning": Fore.YELLOW,
        "error": Fore.RED,
        "critical": Fore.RED + Style.BRIGHT,
    }

    def __call__(self, logger, method_name, event_dict):
        level = event_dict.get("level", "info")
        color = self.LEVEL_COLORS.get(level, "")
        reset = Style.RESET_ALL
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = event_dict.pop("event", "")
        extras = " ".join(f"{k}={v}" for k, v in event_dict.items() if k not in ("level", "timestamp"))
        return f"{color}[{ts}] [{level.upper():7s}]{reset} {msg} {Fore.LIGHTBLACK_EX}{extras}{reset}"


def setup_logging(debug: bool = False):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            ColoredConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "app"):
    return structlog.get_logger(name)
