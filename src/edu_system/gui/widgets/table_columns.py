"""
动态表格列管理器（Sprint 3.7.10）
- 按字段注册表动态生成表格列（系统列 + 自定义字段列合并）
- 列配置持久化：每用户每表 QSettings（显示/顺序/宽度）
"""

import json

from PyQt5.QtCore import QSettings

# 每张表的列配置 key（QSettings 组结构: columns/<table_key>）
_SETTINGS_ORG = "edu_system"
_SETTINGS_APP = "table_columns"


class TableColumnManager:
    """表格列管理：系统列 + FieldDefinition 动态列，配置持久化

    用法:
        mgr = TableColumnManager("student_list", system_columns)
        columns = mgr.build(field_defs)   # 合并并应用用户偏好
        mgr.save_visible(col_keys)        # 持久化显示列
        mgr.save_order(col_keys)          # 持久化顺序
    """

    def __init__(self, table_key: str, system_columns: list | None = None):
        """system_columns: [{"key","label","width","required"}] 系统固定列"""
        self.table_key = table_key
        self.system_columns = system_columns or []
        self._settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)

    # ── 列构建 ──
    def build(self, field_defs: list | None = None) -> list[dict]:
        """合并系统列与动态字段列，应用用户偏好（显示/顺序/宽度）"""
        dynamic = self._field_defs_to_columns(field_defs or [])
        all_cols = self.system_columns + dynamic
        prefs = self._load_prefs()
        if not prefs:
            return all_cols  # 首次使用：全部显示，系统列在前
        return self._apply_prefs(all_cols, prefs)

    def _field_defs_to_columns(self, field_defs: list) -> list[dict]:
        """FieldDefinition → 列定义（key 用 field_key 存 ext_json）"""
        cols = []
        for fd in field_defs:
            key = fd.field_key if hasattr(fd, "field_key") else fd.get("field_key")
            label = fd.label if hasattr(fd, "label") else fd.get("label", key)
            ftype = fd.field_type if hasattr(fd, "field_type") else fd.get("field_type", "string")
            width = 120 if ftype in ("string", "select", "enum") else 90
            cols.append(
                {
                    "key": key,
                    "label": label,
                    "width": width,
                    "is_dynamic": True,
                    "field_type": ftype,
                }
            )
        return cols

    def _apply_prefs(self, all_cols: list[dict], prefs: dict) -> list[dict]:
        """按用户偏好排序/过滤/设宽（保留未记录的新列）"""
        hidden = set(prefs.get("hidden", []))
        order = prefs.get("order", [])
        widths = prefs.get("widths", {})

        result = []
        # 先按用户顺序排列已记录列
        key_to_col = {c["key"]: c for c in all_cols}
        for key in order:
            col = key_to_col.get(key)
            if col and key not in hidden:
                col["width"] = widths.get(key, col["width"])
                result.append(col)
        # 追加用户未记录的新列（保持系统列优先的默认顺序）
        for col in all_cols:
            if col["key"] not in order and col["key"] not in hidden:
                col["width"] = widths.get(col["key"], col["width"])
                result.append(col)
        return result

    # ── 持久化 ──
    def save_visible(self, visible_keys: list):
        """保存当前可见列（并计算 hidden 集）"""
        prefs = self._load_prefs() or {}
        all_keys = {c["key"] for c in self.system_columns}
        prefs["hidden"] = [k for k in all_keys if k not in visible_keys]
        self._save_prefs(prefs)

    def save_order(self, ordered_keys: list):
        """保存列顺序"""
        prefs = self._load_prefs() or {}
        prefs["order"] = ordered_keys
        self._save_prefs(prefs)

    def save_width(self, col_key: str, width: int):
        """保存单列宽度"""
        prefs = self._load_prefs() or {}
        prefs.setdefault("widths", {})[col_key] = width
        self._save_prefs(prefs)

    def reset(self):
        """重置本表列配置"""
        self._settings.remove(self.table_key)

    # ── 内部 ──
    def _load_prefs(self) -> dict | None:
        raw = self._settings.value(self.table_key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return None

    def _save_prefs(self, prefs: dict):
        self._settings.setValue(self.table_key, json.dumps(prefs, ensure_ascii=False))
        self._settings.sync()
