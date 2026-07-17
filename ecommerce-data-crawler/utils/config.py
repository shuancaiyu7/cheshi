# utils/config.py
import configparser
from pathlib import Path


def load_config(config_file: str = "config.ini") -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config_path = Path(config_file)

    if not config_path.is_absolute():
        config_path = Path(__file__).resolve().parent.parent / config_file

    if config_path.exists():
        config.read(config_path, encoding="utf-8")
        print(f"Configuration loaded from: {config_path}")
    else:
        print(f"Warning: Config file not found: {config_path}, using defaults")

    return config


def get_db_url(config: configparser.ConfigParser) -> str:
    db_type = config.get("database", "type", fallback="sqlite")

    if db_type == "sqlite":
        sqlite_path = config.get("database", "sqlite_path", fallback="data/products.db")
        sqlite_path = Path(sqlite_path)
        if not sqlite_path.is_absolute():
            sqlite_path = Path(__file__).resolve().parent.parent / sqlite_path
        return f"sqlite:///{sqlite_path.as_posix()}"
    if db_type == "mysql":
        host = config.get("database", "mysql_host", fallback="localhost")
        port = config.get("database", "mysql_port", fallback="3306")
        user = config.get("database", "mysql_user", fallback="root")
        password = config.get("database", "mysql_password", fallback="")
        database = config.get("database", "mysql_database", fallback="ecommerce_db")
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    return "sqlite:///./data/products.db"


def get_crawler_config(config: configparser.ConfigParser) -> dict:
    return {
        "max_concurrent": config.getint("crawler", "max_concurrent", fallback=3),
        "request_delay": config.getfloat("crawler", "request_delay", fallback=2.0),
        "max_retries": config.getint("crawler", "max_retries", fallback=3),
    }


def get_scraping_config(config: configparser.ConfigParser) -> dict:
    categories_str = config.get("scraping", "categories", fallback="手机数码,笔记本电脑,耳机音箱,智能手表")
    categories = [c.strip() for c in categories_str.split(",") if c.strip()]

    platforms_str = config.get("scraping", "platforms", fallback="jd,tmall")
    platforms = [p.strip() for p in platforms_str.split(",") if p.strip()]

    return {
        "categories": categories,
        "platforms": platforms,
        "items_per_category": config.getint("scraping", "items_per_category", fallback=50),
    }


def _parse_extra_params(raw_value: str) -> dict:
    if not raw_value:
        return {}
    result = {}
    for item in raw_value.split(";"):
        if not item.strip() or "=" not in item:
            continue
        key, value = item.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def get_api_config(config: configparser.ConfigParser) -> dict:
    return {
        "jd": {
            "enabled": config.getboolean("jd_api", "enabled", fallback=False),
            "base_url": config.get("jd_api", "base_url", fallback=""),
            "app_key": config.get("jd_api", "app_key", fallback=""),
            "app_secret": config.get("jd_api", "app_secret", fallback=""),
            "access_token": config.get("jd_api", "access_token", fallback=""),
            "timeout": config.getint("jd_api", "timeout", fallback=30),
            "method": config.get("jd_api", "method", fallback=""),
            "version": config.get("jd_api", "version", fallback="2.0"),
            "sign_method": config.get("jd_api", "sign_method", fallback="md5"),
            "response_path": config.get("jd_api", "response_path", fallback=""),
            "data_path": config.get("jd_api", "data_path", fallback=""),
            "extra_params": _parse_extra_params(config.get("jd_api", "extra_params", fallback="")),
        },
        "tmall": {
            "enabled": config.getboolean("tmall_api", "enabled", fallback=False),
            "base_url": config.get("tmall_api", "base_url", fallback=""),
            "app_key": config.get("tmall_api", "app_key", fallback=""),
            "app_secret": config.get("tmall_api", "app_secret", fallback=""),
            "access_token": config.get("tmall_api", "access_token", fallback=""),
            "timeout": config.getint("tmall_api", "timeout", fallback=30),
            "method": config.get("tmall_api", "method", fallback=""),
            "version": config.get("tmall_api", "version", fallback="2.0"),
            "sign_method": config.get("tmall_api", "sign_method", fallback="md5"),
            "response_path": config.get("tmall_api", "response_path", fallback=""),
            "data_path": config.get("tmall_api", "data_path", fallback=""),
            "extra_params": _parse_extra_params(config.get("tmall_api", "extra_params", fallback="")),
        },
    }
