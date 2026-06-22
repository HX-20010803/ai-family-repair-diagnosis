PRIMARY_CATEGORIES = {
    "water": "水路维修",
    "circuit": "电路维修",
    "appliance": "家电维修",
    "lock_window": "门锁门窗",
    "wall_floor": "墙面地面",
    "kitchen_bath": "厨卫设备",
    "maintenance": "日常保养",
}

SECONDARY_TO_PRIMARY = {
    "water_leak": "water",
    "drain_blocked": "water",
    "ac_not_cooling": "appliance",
    "circuit_trip": "circuit",
    "lock_failure": "lock_window",
    "wall_mold": "wall_floor",
    "water_heater_failure": "appliance",
    "range_hood_gas_stove": "kitchen_bath",
    "floor_drain_smell": "kitchen_bath",
    "window_hardware": "lock_window",
}

SECONDARY_NAMES = {
    "water_leak": "漏水渗水",
    "drain_blocked": "马桶/下水堵塞",
    "ac_not_cooling": "空调不制冷",
    "circuit_trip": "电路跳闸",
    "lock_failure": "门锁故障",
    "wall_mold": "墙面发霉/墙皮脱落",
    "water_heater_failure": "热水器故障",
    "range_hood_gas_stove": "油烟机/燃气灶问题",
    "floor_drain_smell": "地漏反味/厨卫异味",
    "window_hardware": "门窗五金/纱窗损坏",
}


CLASSIFICATION_KEYWORDS = {
    "water_leak": ["漏水", "渗水", "滴水", "水龙头", "天花板", "吊顶", "水印", "水痕", "水表", "角阀"],
    "drain_blocked": ["马桶", "堵", "返水", "下水慢", "下水很慢", "地漏不下水", "疏通", "水槽", "排水", "冒泡", "冲水"],
    "ac_not_cooling": ["空调", "不制冷", "不冷", "制冷慢", "外机"],
    "circuit_trip": ["跳闸", "插座", "插排", "配电箱", "焦味", "冒烟", "漏电", "电路", "线路", "火花", "烧焦", "发烫", "漏保", "灯不亮", "灯泡", "闪烁", "没电"],
    "lock_failure": ["门锁", "打不开", "钥匙", "指纹锁", "被困", "门把手", "智能锁", "指纹", "反锁", "锁舌", "胶水", "备用钥匙", "机械锁"],
    "wall_mold": ["发霉", "墙皮", "鼓包", "返潮", "墙角", "墙面", "小黑点", "起皮", "霉味", "霉斑", "墙砖", "地脚线", "吊顶边缘", "脱落"],
    "water_heater_failure": ["热水器", "电热水器", "燃气热水器", "不出热水", "忽冷忽热", "故障码", "泄压阀", "水温", "加热", "面板"],
    "range_hood_gas_stove": ["燃气灶", "煤气灶", "油烟机", "燃气味", "煤气味", "燃气管", "灶台", "点不着", "打不着火", "漏油", "火苗", "点火"],
    "floor_drain_smell": ["反味", "返味", "臭味", "异味", "地漏", "水封", "下水道味", "下水道", "更臭", "味道", "地漏盖", "排风扇", "防臭芯"],
    "window_hardware": ["窗户", "纱窗", "关不严", "五金", "松动", "变形", "推拉门", "轨道", "卡住", "阳台门", "门窗", "密封条", "玻璃门", "合页", "推拉窗", "裂纹", "玻璃裂"],
}


def primary_for_secondary(secondary: str) -> str:
    return SECONDARY_TO_PRIMARY.get(secondary, "maintenance")
