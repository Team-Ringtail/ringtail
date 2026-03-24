"""
UI helper utilities for the Ringtail dashboard.
"""


def ui_value(
    data: dict | list | str | int | float | bool | None,
    key: str,
    fallback: dict | list | str | int | float | bool | None
) -> dict | list | str | int | float | bool | None {
    if data is None {
        return fallback;
    }
    if key in data {
        return data[key];
    }
    return fallback;
}


def ui_basename(path: str) -> str {
    parts = str(path).split("/");
    if len(parts) == 0 {
        return str(path);
    }
    return str(parts[len(parts) - 1]);
}


def ui_format_demo_benchmarks(data: dict) -> str {
    lines: list = [];
    for item in ui_value(data, "benchmarks", []) {
        lines.append(
            str(ui_value(item, "label", "")) + " -> "
            + str(ui_value(item, "description", ""))
        );
    }
    return "\n".join(lines);
}


def ui_get_query_param(name: str) -> str {
    search = str(globalThis.window.location.search or "");
    if search == "" {
        return "";
    }
    if len(search) > 0 and search[0] == "?" {
        search = search[1:];
    }
    parts = search.split("&");
    for part in parts {
        pieces = part.split("=");
        if len(pieces) >= 2 and pieces[0] == name {
            return str(globalThis.decodeURIComponent(pieces[1]));
        }
    }
    return "";
}


def ui_new_job_id(prefix: str) -> str {
    if "crypto" in globalThis and globalThis.crypto != None and "randomUUID" in globalThis.crypto {
        return prefix + "-" + str(globalThis.crypto.randomUUID());
    }
    ts = str(int(globalThis.Date.now()));
    rand = str(int(globalThis.Math.floor(globalThis.Math.random() * 1000000)));
    return prefix + "-" + ts + "-" + rand;
}


def ui_format_log_text(lines: list) -> str {
    if len(lines) == 0 {
        return "Live run events will appear here.";
    }
    return "\n".join(lines);
}


def ui_parse_expected_value(raw: str) -> dict | list | str | int | float | bool | None {
    text = str(raw).strip();
    if text == "" {
        return None;
    }
    try {
        return globalThis.JSON.parse(text);
    } except Exception as err {
        return text;
    }
}


def ui_set_theme_attr(theme: str) -> None {
    if theme not in ["light", "dark"] {
        return;
    }
    if "document" not in globalThis or globalThis.document is None {
        return;
    }
    if "documentElement" in globalThis.document and globalThis.document.documentElement != None {
        globalThis.document.documentElement.setAttribute("data-theme", theme);
    }
}


def ui_save_theme(theme: str) -> None {
    try {
        globalThis.localStorage.setItem("ringtail_theme", theme);
    } except Exception as err {
        ignored = str(err);
    }
}


def ui_load_theme(default_theme: str = "dark") -> str {
    theme = default_theme;
    try {
        saved = str(globalThis.localStorage.getItem("ringtail_theme") or "");
        if saved in ["light", "dark"] {
            theme = saved;
        }
    } except Exception as err {
        ignored = str(err);
    }
    return theme;
}
