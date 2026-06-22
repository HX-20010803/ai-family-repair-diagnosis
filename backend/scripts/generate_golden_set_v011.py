from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = BACKEND_DIR / "eval"
OUTPUT_PATH = EVAL_DIR / "golden_set_v0.1.1_200.jsonl"
NOTES_PATH = EVAL_DIR / "golden_set_v0.1.1_notes.md"


def item(text: str, urgency: str, high_risk: bool, path: str, risk_type: str | None = None) -> dict:
    return {
        "input": text,
        "urgency": urgency,
        "is_high_risk": high_risk,
        "risk_type": risk_type,
        "expected_path": path,
    }


CATEGORIES = [
    {
        "secondary": "water_leak",
        "primary": "water",
        "name": "漏水渗水",
        "samples": [
            item("卫生间天花板一直滴水，靠近吊顶灯", "S", True, "先远离灯具和开关，必要时断电，联系物业或水电师傅", "water_near_electric"),
            item("客厅灯旁边有水印，今天开始往下滴水", "S", True, "停止使用附近电器，拍照留证，尽快联系物业排查楼上或管道", "water_near_electric"),
            item("阳台漏水流到插座下面了，现在墙上都是湿的", "S", True, "先断开相关区域电源，不触碰插座，联系专业人员处理", "water_near_electric"),
            item("厨房顶上漏水，水滴到油烟机插座附近", "S", True, "先停止使用油烟机和插座，断电后联系物业或水电师傅", "water_near_electric"),
            item("卫生间漏水已经流到电热水器旁边", "S", True, "停止使用热水器和附近电器，联系物业和专业维修", "water_near_electric"),
            item("墙里像有水流声，配电箱旁边墙面发潮", "S", True, "不要自行拆配电箱，先断开风险回路并联系物业水电工", "water_near_electric"),
            item("楼上漏水很严重，水已经滴到灯罩里", "S", True, "不要开灯，关闭相关电源，立即联系物业和楼上住户", "water_near_electric"),
            item("洗手池下面漏水，旁边插排也被打湿了", "S", True, "停止使用插排并断电，擦干前不要通电，联系水电师傅", "water_near_electric"),
            item("卫生间天花板一直滴水，地面已经湿了一片", "A", False, "拍照记录位置和持续时间，联系物业确认楼上或公共管道"),
            item("厨房水槽下面渗水，柜子里都是潮的", "A", False, "先关闭水槽下方角阀，清理积水，预约水电维修"),
            item("洗衣机旁边地面总有一滩水", "A", False, "检查进水管和排水管接口，无法确认时联系师傅"),
            item("墙角这两天一直渗水，面积越来越大", "A", False, "标记渗水范围，联系物业排查外墙或暗管"),
            item("水龙头关紧了还滴水，已经滴了一晚上", "B", False, "可先关闭角阀，记录情况，预约更换阀芯或龙头"),
            item("厨房下水柜里有点潮，不确定是不是漏水", "B", False, "擦干后观察是否再次变湿，检查软管接口"),
            item("阳台窗边下雨后会渗水", "B", False, "记录雨天渗水位置，排查窗框密封和外墙"),
            item("马桶后面地上有水，但没有一直流", "B", False, "擦干观察来源，检查水箱、软管和法兰位置"),
            item("洗手盆下面偶尔有水珠", "C", False, "先观察接口冷凝或轻微渗漏，必要时预约检修"),
            item("厨房台面边缘有点渗水，不确定从哪来", "C", False, "擦干并分区观察，补充位置和持续时间"),
            item("墙面有水印但现在没滴水", "B", False, "确认是否扩大或返潮，必要时联系物业排查"),
            item("水表附近地面湿湿的，家里用水量也变大", "A", False, "关闭总阀观察水表，联系物业或水电师傅排查暗漏"),
        ],
    },
    {
        "secondary": "drain_blocked",
        "primary": "water",
        "name": "马桶/下水堵塞",
        "samples": [
            item("马桶堵了水下不去，水快漫出来了", "A", False, "停止继续冲水，先确认是否返水，必要时联系疏通"),
            item("马桶堵了还有臭水往外冒，卫生间地上都是水", "A", False, "不要继续冲水，清理外溢污水，联系管道疏通"),
            item("厕所下水完全不动，冲一次水位就升高", "A", False, "停止冲水，判断是否硬物堵塞，联系专业疏通"),
            item("厨房水槽一放水就从地漏冒上来", "A", False, "停止大量放水，检查是否主管堵塞，联系物业或疏通"),
            item("地漏返水到客厅插座附近了", "S", True, "先远离插座并断电，停止用水，联系物业和疏通人员", "water_near_electric"),
            item("厨房返水流到冰箱插座旁边，地面很湿", "S", True, "停止用水并断开附近电源，联系物业和专业疏通", "water_near_electric"),
            item("卫生间返水把插排泡了，还能继续用吗", "S", True, "不要继续使用插排，先断电并处理积水，联系专业人员", "water_near_electric"),
            item("洗澡时地漏下水很慢，水会积到脚踝", "B", False, "可先清理地漏毛发，避免强腐蚀疏通剂，仍不通再报修"),
            item("厨房下水慢，过一会儿才下去", "B", False, "先清理滤网和存水弯，观察是否主管堵塞"),
            item("洗手盆下水越来越慢，有咕噜声", "B", False, "检查存水弯和毛发堵塞，必要时预约疏通"),
            item("马桶偶尔堵，冲两次才下去", "B", False, "减少反复冲水，观察是否纸巾或硬物堵塞"),
            item("马桶里面掉了塑料盖，现在冲不下去", "A", False, "不要强行冲水，避免硬物进入更深管道，联系疏通"),
            item("卫生间地漏有头发堵住，水下得慢", "C", False, "戴手套清理地漏盖和毛发，避免拆深处管道"),
            item("厨房水池过滤网拿掉后还是下水慢", "B", False, "检查存水弯油污，仍慢则联系疏通"),
            item("洗衣机排水时地漏会冒泡", "B", False, "检查排水管插入深度和地漏通畅度"),
            item("马桶冲水没劲，但不是完全堵", "B", False, "检查水箱水位和排水阀，补充是否返水"),
            item("厕所反味加上下水慢，不知道是不是堵了", "B", False, "先判断返水和水封情况，必要时清理或疏通"),
            item("阳台地漏下雨时会返水", "A", False, "可能涉及公共排水，联系物业排查主管"),
            item("厨房主管好像堵了，楼下也说有返水", "A", False, "停止排水，联系物业处理公共管道"),
            item("马桶堵了但水还能慢慢下去", "B", False, "先不要连续冲水，可尝试低风险皮搋子疏通"),
        ],
    },
    {
        "secondary": "ac_not_cooling",
        "primary": "appliance",
        "name": "空调不制冷",
        "samples": [
            item("空调开了半小时还是不制冷，外机也不怎么转", "B", False, "确认模式和温度，检查外机运行，必要时联系售后"),
            item("空调有风但是一点都不凉", "B", False, "检查是否制冷模式、滤网是否堵塞，仍异常联系维修"),
            item("空调显示 E6，房间降不下来", "B", False, "记录故障码和品牌型号，联系售后或维修"),
            item("空调室内机滴水还不制冷，插座下面有水", "S", True, "停止使用并远离插座，断电后联系空调售后", "water_near_electric"),
            item("空调开机后跳闸，重新开又跳", "S", True, "不要反复合闸，停止使用并联系电工或空调售后", "electric"),
            item("空调用了十年，制冷越来越差", "B", False, "检查滤网和外机散热，评估清洗或检修"),
            item("空调刚清洗过但还是不冷", "B", False, "补充外机是否运行、铜管是否结霜，联系售后检测"),
            item("空调遥控显示制冷，但吹出来是热风", "B", False, "确认模式和设定温度，排查四通阀或控制异常"),
            item("空调外机声音很大，制冷很慢", "B", False, "观察外机风扇和散热环境，预约检修"),
            item("空调滤网很脏，会影响制冷吗", "C", False, "可先断电清洗滤网，晾干后再使用"),
            item("空调开一会儿就自动停机", "B", False, "记录停机时间和故障码，检查外机散热"),
            item("空调内机有霜，不怎么制冷", "B", False, "停止长时间运行，联系售后检测制冷剂或传感器"),
            item("房间很热，空调要开很久才凉", "C", False, "确认匹数、门窗密封和滤网清洁情况"),
            item("空调显示尘满，不制冷是不是坏了", "C", False, "优先清洁滤网并复位提示，再观察制冷效果"),
            item("空调外机不转，室内机有风", "B", False, "停止长时间试机，联系售后检查外机供电和电容"),
            item("空调制冷时有异味", "C", False, "优先清洁滤网和蒸发器，必要时深度清洗"),
            item("空调漏水到地板上，但还能制冷", "B", False, "停止长时间使用，检查排水管堵塞或安装坡度"),
            item("新空调装完第一天就不制冷", "B", False, "联系安装售后，检查安装和制冷剂"),
            item("空调外机被杂物挡住，会不会影响制冷", "C", False, "清理外机周边通风空间，保持散热"),
            item("空调制冷一阵一阵的，不稳定", "B", False, "记录运行规律和故障码，联系售后检测"),
        ],
    },
    {
        "secondary": "circuit_trip",
        "primary": "electric",
        "name": "电路跳闸/插座冒烟",
        "samples": [
            item("插座发黑还有焦味，现在还能继续用吗", "S", True, "立即停止使用，断电，联系专业电工", "electric_smoke"),
            item("插座刚才冒烟了，墙上也有黑印", "S", True, "不要继续通电，关闭电源并联系电工现场处理", "electric_smoke"),
            item("开热水壶时插座有火花", "S", True, "停止使用该插座和电器，断电后找电工检查", "electric_smoke"),
            item("家里配电箱有焦味，还嗡嗡响", "S", True, "不要自行拆配电箱，关闭总闸并联系电工", "electric_smoke"),
            item("卫生间插座被水溅湿后跳闸了", "S", True, "不要反复合闸，保持远离，联系电工检查漏电", "electric_water"),
            item("灯一开就闪火花，开关面板发热", "S", True, "停止使用开关，断开回路，联系专业电工", "electric_smoke"),
            item("全屋突然跳闸，还有烧焦味", "S", True, "不要反复合闸，关闭总闸，联系电工排查", "electric_smoke"),
            item("插排进水了还插着电，怎么办", "S", True, "不要触碰插排，先断电，确认干燥和安全后再处理", "electric_water"),
            item("空调插座摸起来发烫", "S", True, "停止使用空调和插座，联系电工检查负载和线路", "electric_smoke"),
            item("厨房插座噼啪响，有一点烟", "S", True, "立即断电，停止使用厨房插座，联系电工", "electric_smoke"),
            item("家里一用电磁炉就跳闸", "A", False, "停止反复试用，检查负载和回路，联系电工"),
            item("某个房间灯不亮，其他地方正常", "B", False, "检查灯泡和开关，仍异常联系电工"),
            item("全屋跳闸但没有焦味，合闸又跳", "A", False, "不要多次强行合闸，逐路排查或联系电工"),
            item("洗衣机一启动就跳闸", "A", False, "停止使用洗衣机，检查插座和电器漏电风险"),
            item("客厅插座没电了，但没有烧焦味", "B", False, "检查空气开关和其他插座，必要时联系电工"),
            item("灯泡频繁闪烁，是线路问题吗", "B", False, "先更换灯泡测试，仍闪烁则检查线路"),
            item("插座松了，插头容易掉", "B", False, "停止大功率使用，预约更换插座面板"),
            item("厨房漏保经常跳，但找不到原因", "A", False, "记录触发电器，联系电工检测漏电"),
            item("新装的插座没电", "B", False, "检查接线和回路，建议由电工处理"),
            item("卧室开灯偶尔跳闸，没有异味", "A", False, "停止反复合闸，排查灯具或开关线路"),
        ],
    },
    {
        "secondary": "lock_failure",
        "primary": "door_window",
        "name": "门锁故障",
        "samples": [
            item("门锁打不开，老人和孩子被锁在屋里", "S", True, "优先确认人身安全，联系物业、正规开锁或应急救援", "trapped"),
            item("指纹锁坏了，小孩一个人在家出不来", "S", True, "保持联系安抚，联系物业和正规开锁，必要时报警求助", "trapped"),
            item("门反锁了，家里老人打不开门", "S", True, "优先联系物业或应急开锁，必要时拨打救援电话", "trapped"),
            item("防盗门打不开，里面有人说头晕", "S", True, "立即联系应急救援和正规开锁，优先处理人员安全", "trapped"),
            item("门锁卡死，人被困在卫生间里", "S", True, "先确认通风和人员状态，联系物业或开锁救援", "trapped"),
            item("智能锁没电，孩子在屋里，备用钥匙也打不开", "S", True, "不要暴力拆门延误，联系物业、开锁或应急救援", "trapped"),
            item("门锁打不开，但人在门外，不着急", "A", False, "确认钥匙和电池情况，联系正规开锁或物业"),
            item("指纹锁提示低电量，门还能打开", "C", False, "及时更换电池，测试备用钥匙"),
            item("钥匙插进去转不动", "B", False, "不要强拧，尝试备用钥匙，必要时找锁匠"),
            item("门把手松了，开关门很费劲", "B", False, "减少用力拉拽，预约维修或更换五金"),
            item("智能锁识别不了指纹，但密码能开", "C", False, "清洁识别区域，重新录入指纹或检查电池"),
            item("门锁里面有异响，担心哪天打不开", "B", False, "预约检查锁体，避免故障扩大"),
            item("钥匙断在锁孔里了", "A", False, "不要继续插拔，联系正规开锁取断钥匙"),
            item("门关上后自动反锁，家人进不来", "B", False, "检查设置和锁舌，必要时联系售后"),
            item("租房门锁不太灵，房东让我自己修", "B", False, "记录故障并联系房东或正规维修"),
            item("门锁电池没电了，外面有应急供电口吗", "C", False, "查看说明书或品牌售后，使用应急供电后尽快换电池"),
            item("门锁打不开，外面下雨进不了屋", "A", False, "联系物业或正规开锁，保留开锁记录"),
            item("门锁被胶水堵了", "A", False, "不要强行转钥匙，联系物业和正规开锁"),
            item("门锁偶尔打不开，多试几次才行", "B", False, "预约检查锁芯和锁体，避免完全失效"),
            item("机械锁锁舌弹不出来", "B", False, "减少强关门，检查锁舌和门框位置"),
        ],
    },
    {
        "secondary": "wall_mold",
        "primary": "wall_floor",
        "name": "墙面发霉/墙皮脱落",
        "samples": [
            item("墙角发霉越来越大，靠近卫生间", "B", False, "记录面积变化，排查卫生间渗漏和通风"),
            item("儿童房墙面发霉，有很重霉味", "B", False, "加强通风除湿，尽快排查潮湿来源"),
            item("墙皮鼓包脱落，下面摸起来潮", "B", False, "不要只刷漆遮盖，先排查渗水或返潮"),
            item("插座周围墙面返潮发霉", "S", True, "停止使用该插座，联系电工和维修人员排查", "water_near_electric"),
            item("墙面渗水流到开关下面了", "S", True, "不要触碰开关，先断电并联系物业排查", "water_near_electric"),
            item("外墙一到下雨就发霉", "B", False, "记录雨天情况，联系物业排查外墙防水"),
            item("卫生间外侧墙皮脱落", "B", False, "重点排查卫生间防水和管道渗漏"),
            item("衣柜后面的墙发霉了", "C", False, "先通风除湿，检查是否贴外墙或有冷凝"),
            item("墙面有小黑点，擦掉又长出来", "B", False, "排查湿度和通风，必要时处理基层"),
            item("墙角返潮但没有漏水痕迹", "C", False, "先测湿度和通风，观察是否季节性冷凝"),
            item("新装修半年墙皮就掉了", "B", False, "保留照片，联系装修方排查基层或防水"),
            item("墙面鼓起一个大包", "B", False, "不要直接戳破，先判断是否潮湿或空鼓"),
            item("厨房墙砖边缘发霉", "C", False, "清洁霉斑并检查密封胶和通风"),
            item("卧室靠窗墙面起皮", "C", False, "检查窗框渗水和冷凝，保持通风"),
            item("地脚线附近墙面发黑", "B", False, "排查地面返潮或管道渗漏"),
            item("墙面有水痕但已经干了", "B", False, "观察是否复发，记录位置和天气关系"),
            item("地下室墙面返潮发霉", "B", False, "加强除湿并排查防水和排水"),
            item("吊顶边缘发霉，楼上是卫生间", "A", False, "联系物业和楼上排查渗漏来源"),
            item("墙皮掉了一块，里面是干的", "C", False, "可先观察基层，必要时局部修补"),
            item("墙面霉味很重但看不到明显霉斑", "C", False, "检查家具背后和通风死角，补充照片或位置"),
        ],
    },
    {
        "secondary": "water_heater_failure",
        "primary": "appliance",
        "name": "热水器故障",
        "samples": [
            item("燃气热水器不出热水，还有燃气味", "S", True, "立即关阀通风，不开关电器，联系燃气公司或售后", "gas"),
            item("热水器附近闻到煤气味，还能洗澡吗", "S", True, "停止使用，关闭燃气阀，通风并联系专业人员", "gas"),
            item("燃气热水器打火失败，厨房有刺鼻气味", "S", True, "不要反复点火，关阀通风，联系燃气公司", "gas"),
            item("电热水器漏水到插座附近", "S", True, "停止使用并断电，联系售后或水电师傅", "water_near_electric"),
            item("热水器插头发烫，还有焦味", "S", True, "立即断电停止使用，联系电工和售后", "electric_smoke"),
            item("洗澡时热水器漏电麻手", "S", True, "立即停止洗澡和使用热水器，断电并联系专业维修", "electric_shock"),
            item("电热水器不出热水，面板正常亮", "B", False, "检查温度设置和加热状态，联系售后检测"),
            item("热水器忽冷忽热", "B", False, "确认水压和燃气供应，记录故障码"),
            item("热水器显示 E1，不知道什么意思", "B", False, "记录品牌型号和故障码，联系售后"),
            item("热水器用了八年，最近加热很慢", "B", False, "考虑水垢或加热管问题，预约清洗或检修"),
            item("燃气热水器打不着火，但没有燃气味", "B", False, "检查电池、水压和燃气阀，仍异常联系售后"),
            item("热水器出水量很小", "B", False, "检查花洒和进水滤网，必要时清洗"),
            item("热水器有异响但能用", "B", False, "不要长期忽视，记录异响并预约检修"),
            item("热水器水温上不去", "B", False, "确认设定温度和用水量，联系售后检测"),
            item("热水器泄压阀滴水", "B", False, "少量滴水可观察，持续漏水需联系售后"),
            item("太阳能热水器不热", "C", False, "检查天气、水位和阀门状态"),
            item("热水器遥控器没反应", "C", False, "先更换电池或检查配对"),
            item("热水器刚开有冷水，要等很久", "C", False, "确认管路距离和循环功能，属于常见现象可继续观察"),
            item("热水器出水有铁锈色", "B", False, "停止饮用，检查内胆或管路锈蚀"),
            item("热水器保养灯亮了", "C", False, "按说明书预约保养或复位提醒"),
        ],
    },
    {
        "secondary": "range_hood_gas_stove",
        "primary": "kitchen_bath",
        "name": "油烟机/燃气灶问题",
        "samples": [
            item("燃气灶打不着火，还有明显燃气味", "S", True, "立即关阀通风，不开关电器，联系燃气公司", "gas"),
            item("厨房一进门就有煤气味，灶也点不着", "S", True, "关闭燃气总阀，开窗通风，远离明火和电器开关", "gas"),
            item("燃气灶关了以后还有气味", "S", True, "关闭阀门并通风，联系燃气公司检测泄漏", "gas"),
            item("燃气管附近有刺鼻味，能不能自己拧紧", "S", True, "不要自行拆接燃气管，关阀通风并联系专业人员", "gas"),
            item("灶台下面闻到燃气味，插座还在旁边", "S", True, "不要触碰插座，关阀通风，联系燃气公司", "gas"),
            item("燃气灶点火时砰的一声还有味道", "S", True, "停止使用，关阀通风，联系燃气维修", "gas"),
            item("油烟机插座冒火花", "S", True, "停止使用油烟机，断电并联系电工", "electric_smoke"),
            item("油烟机漏油滴到插座上", "S", True, "停止使用并断电，清理前先确认电源安全", "electric_smoke"),
            item("燃气灶火苗突然变黄，还闻到气味", "S", True, "停止使用，通风并联系燃气公司检测", "gas"),
            item("厨房有燃气味但我不确定是不是泄漏", "S", True, "按疑似燃气泄漏处理，关阀通风并联系专业人员", "gas"),
            item("油烟机吸力变小，炒菜味道散不出去", "B", False, "检查滤网和烟道，安排清洗或检修"),
            item("油烟机声音很大还抖", "B", False, "停止长时间运行，检查安装和风轮积油"),
            item("燃气灶打不着火，但没有燃气味", "B", False, "检查电池、点火针和燃气阀，仍异常联系售后"),
            item("燃气灶松手就熄火", "B", False, "检查热电偶和火盖位置，联系维修"),
            item("油烟机灯亮但电机不转", "B", False, "停止反复开关，联系售后检测电机或电容"),
            item("油烟机需要清洗了吗，吸力不太行", "C", False, "可先清洗滤网和油杯，观察吸力恢复情况"),
            item("燃气灶火苗一边大一边小", "B", False, "清理火盖孔，仍异常联系售后"),
            item("油烟机油杯满了会不会影响吸力", "C", False, "及时清理油杯和滤网，避免油污滴漏"),
            item("燃气灶按下去没有哒哒声", "B", False, "检查电池和点火装置，联系维修"),
            item("油烟机排烟管掉了", "A", False, "停止使用油烟机，重新固定排烟管或联系安装维修"),
        ],
    },
    {
        "secondary": "floor_drain_smell",
        "primary": "kitchen_bath",
        "name": "地漏反味/厨卫异味",
        "samples": [
            item("卫生间地漏一直反味，味道很重", "B", False, "检查水封和地漏芯，清洁后观察是否改善"),
            item("厨房下水道反味，开窗也散不掉", "B", False, "检查存水弯和密封，必要时联系疏通"),
            item("地漏反味还返水，水漫到插座旁边", "S", True, "先断开附近电源，停止用水，联系物业和疏通人员", "water_near_electric"),
            item("厨房下水返水把插排泡了", "S", True, "不要触碰插排，先断电并处理返水", "water_near_electric"),
            item("卫生间长期不用，一进去有臭味", "C", False, "补水恢复水封，清洁地漏并保持通风"),
            item("洗手盆下面柜子有下水道味", "B", False, "检查排水管和存水弯密封"),
            item("地漏有虫子和臭味", "B", False, "清洁地漏并检查防臭芯，必要时更换"),
            item("厕所味道像下水道，但没有返水", "B", False, "检查地漏、水封和马桶法兰密封"),
            item("厨房水槽反味，放水后更明显", "B", False, "检查存水弯是否缺失或漏气"),
            item("阳台地漏反味，平时很少用", "C", False, "向地漏补水，观察水封是否恢复"),
            item("马桶周围有臭味，不确定是不是地漏", "B", False, "检查马桶法兰和地漏水封"),
            item("卫生间排风扇一开反而更臭", "B", False, "检查负压导致返味，补充地漏和排风情况"),
            item("厨房下水慢还反味", "B", False, "先清理存水弯和油污，必要时疏通"),
            item("地漏盖拿掉后味道特别大", "C", False, "检查防臭芯是否缺失或损坏"),
            item("雨天卫生间会反味", "B", False, "记录发生时间，排查管道气压和水封"),
            item("洗衣机地漏有臭味", "B", False, "检查洗衣机排水管和地漏密封"),
            item("新房卫生间反味，是不是装修问题", "B", False, "检查地漏、防臭芯和马桶法兰安装"),
            item("地漏水封干了会反味吗", "C", False, "补水观察，长期不用可定期补水"),
            item("下水道味道突然很浓", "B", False, "检查是否返水、堵塞或公共管道异常"),
            item("厨房橱柜里面有臭味", "B", False, "检查下水管接口密封和存水弯"),
        ],
    },
    {
        "secondary": "window_hardware",
        "primary": "door_window",
        "name": "门窗五金/纱窗损坏",
        "samples": [
            item("高层窗户关不严，外面风大窗扇晃动", "S", True, "远离窗边，不要强行操作，联系物业或门窗师傅", "falling_object"),
            item("窗户合页松了，感觉玻璃要掉下来", "S", True, "停止开关窗，远离下方区域，联系专业人员处理", "falling_object"),
            item("阳台窗户玻璃裂了，高层会不会掉", "S", True, "远离破裂玻璃，避免震动，联系专业人员更换", "glass_break"),
            item("外开窗把手坏了，窗户在高层关不上", "S", True, "不要探身处理，联系物业或门窗师傅", "falling_object"),
            item("窗户关不严有松动", "B", False, "检查五金和密封条，预约门窗维修"),
            item("纱窗破了一个大洞", "C", False, "可更换纱网或预约门窗维修"),
            item("推拉门很难推，轨道像卡住了", "B", False, "清理轨道异物，仍卡顿则检查滑轮"),
            item("窗户漏风很明显", "B", False, "检查密封条老化和锁点调节"),
            item("窗户把手松了但还能关", "B", False, "减少频繁开关，预约更换把手或螺丝固定"),
            item("纱窗推不动了", "C", False, "检查轨道积灰和滑轮，必要时更换"),
            item("窗户下雨会从缝里进水", "B", False, "记录渗水位置，检查密封胶和排水孔"),
            item("阳台门关不上，卡在一半", "B", False, "不要强推，检查轨道和滑轮"),
            item("门窗密封条脱落", "C", False, "可更换密封条，改善漏风和噪音"),
            item("窗户锁点卡住了", "B", False, "不要强拧把手，预约门窗五金维修"),
            item("玻璃门合页异响", "C", False, "检查合页固定和润滑，必要时调整"),
            item("纱窗框变形，蚊子能进来", "C", False, "更换纱窗框或调整轨道"),
            item("窗户开关时会掉金属碎屑", "B", False, "减少使用，检查五金磨损"),
            item("卧室窗户关上还有缝", "B", False, "检查锁点、合页和密封条"),
            item("推拉窗轨道积水", "B", False, "清理排水孔，检查密封和坡度"),
            item("窗户玻璃有小裂纹但不在高层", "A", False, "减少震动，尽快预约更换玻璃"),
        ],
    },
]


def build_samples() -> list[dict]:
    samples: list[dict] = []
    sequence = 1
    for category in CATEGORIES:
        if len(category["samples"]) != 20:
            raise ValueError(f"{category['secondary']} must have exactly 20 samples")
        for row in category["samples"]:
            expected = {
                "primary": category["primary"],
                "secondary": category["secondary"],
                "urgency": row["urgency"],
                "is_high_risk": row["is_high_risk"],
                "expected_path": row["expected_path"],
            }
            if row["risk_type"]:
                expected["risk_type"] = row["risk_type"]
            samples.append(
                {
                    "id": f"gold_v011_{sequence:03d}",
                    "input": row["input"],
                    "expected": expected,
                    "meta": {
                        "scenario_name": category["name"],
                        "source": "ai_generated_candidate",
                        "review_status": "pending_human_review",
                    },
                }
            )
            sequence += 1
    return samples


def validate(samples: list[dict]) -> None:
    counts = Counter(sample["expected"]["secondary"] for sample in samples)
    high_risk_count = sum(1 for sample in samples if sample["expected"]["is_high_risk"])
    if len(samples) != 200:
        raise ValueError(f"Expected 200 samples, got {len(samples)}")
    if len(counts) != 10:
        raise ValueError(f"Expected 10 secondary categories, got {len(counts)}")
    if any(count != 20 for count in counts.values()):
        raise ValueError(f"Every category must have 20 samples: {counts}")
    if high_risk_count < 50:
        raise ValueError(f"Expected at least 50 high-risk samples, got {high_risk_count}")


def write_notes(samples: list[dict]) -> None:
    counts = Counter(sample["expected"]["secondary"] for sample in samples)
    high_risk_counts = Counter(
        sample["expected"]["secondary"] for sample in samples if sample["expected"]["is_high_risk"]
    )
    lines = [
        "# Golden Set v0.1.1 说明",
        "",
        "本文件是 PRD 第 21.4 要求的 200 条人工标注黄金集候选版。",
        "",
        "## 生成原则",
        "",
        "- 覆盖 MVP 10 类故障场景，每类 20 条。",
        "- 覆盖标准表达、口语表达、信息不足、高风险、否定/边界和混合线索。",
        "- 每条包含二级分类、一级分类、紧急等级、是否高风险和推荐处理路径。",
        "- 当前标记为 `ai_generated_candidate`，进入外测前需要人工重点审核高风险和争议样本。",
        "",
        "## 分布",
        "",
        "secondary | samples | high_risk",
        "--- | ---: | ---:",
    ]
    for secondary in sorted(counts):
        lines.append(f"{secondary} | {counts[secondary]} | {high_risk_counts[secondary]}")
    lines.extend(
        [
            "",
            f"- Total samples: {len(samples)}",
            f"- High-risk samples: {sum(high_risk_counts.values())}",
            "",
            "## 人工审核建议",
            "",
            "优先审核：",
            "",
            "1. 所有 `is_high_risk=true` 样本。",
            "2. S/A 临界样本。",
            "3. 带否定或不确定表达的燃气、电路、漏水样本。",
            "4. 用户真实外测新增的错分样本。",
        ]
    )
    NOTES_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    samples = build_samples()
    validate(samples)
    OUTPUT_PATH.write_text(
        "\n".join(json.dumps(sample, ensure_ascii=False, separators=(",", ":")) for sample in samples) + "\n",
        encoding="utf-8",
    )
    write_notes(samples)
    print(json.dumps({"output": str(OUTPUT_PATH), "notes": str(NOTES_PATH), "samples": len(samples)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
