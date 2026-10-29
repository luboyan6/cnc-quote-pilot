import { ref, computed } from "vue";
import CncPartConfigAPI, { type CncParamsCatalog } from "@/api/module_cnc/cnc_part_config";

/** 嘉立创 CNC 内置参数与约束元数据 */
export const JLC_DEFAULT_CATALOG = {
  "material_categories": [
    "铝合金",
    "合金钢",
    "不锈钢",
    "铜合金",
    "塑料"
  ],
  "materials": [
    {
      "name": "不锈钢-304",
      "category": "不锈钢",
      "code": "SUS304",
      "supported_finishes": [
        "钝化",
        "镀镍",
        "激光打标",
        "拉丝",
        "仅喷砂"
      ],
      "supported_tolerances": [
        "GB/T 1804-2000 m级",
        "±0.10mm",
        "±0.05mm"
      ],
      "supported_roughnesses": [
        "严格外观",
        "常规外观"
      ],
      "thickness_limit": {
        "min_mm": 0.01,
        "max_mm": 150
      },
      "guidance": ""
    },
    {
      "name": "45#钢",
      "category": "合金钢",
      "code": "G45",
      "supported_finishes": [
        "钝化",
        "镀镍",
        "发黑",
        "激光打标",
        "拉丝",
        "仅喷砂"
      ],
      "supported_tolerances": [
        "GB/T 1804-2000 m级",
        "±0.10mm",
        "±0.05mm"
      ],
      "supported_roughnesses": [
        "严格外观",
        "常规外观"
      ],
      "thickness_limit": {
        "min_mm": 4,
        "max_mm": 220
      },
      "guidance": ""
    },
    {
      "name": "Q235钢（A3钢）",
      "category": "合金钢",
      "code": "Q235",
      "supported_finishes": [
        "钝化",
        "镀镍",
        "发黑",
        "激光打标",
        "拉丝",
        "仅喷砂"
      ],
      "supported_tolerances": [
        "GB/T 1804-2000 m级",
        "±0.10mm",
        "±0.05mm"
      ],
      "supported_roughnesses": [
        "严格外观",
        "常规外观"
      ],
      "thickness_limit": {
        "min_mm": 4,
        "max_mm": 220
      },
      "guidance": ""
    },
    {
      "name": "工程塑料-ABS（白色）",
      "category": "塑料",
      "code": "P111",
      "supported_finishes": [
        "喷油",
        "UV打印"
      ],
      "supported_tolerances": [
        "GB/T 1804-2000 m级",
        "±0.10mm",
        "±0.05mm"
      ],
      "supported_roughnesses": [
        "严格外观",
        "常规外观"
      ],
      "thickness_limit": {
        "min_mm": 1,
        "max_mm": 9999
      },
      "guidance": "ABS不喷油表面容易有磨损划痕，喷油后表面更光滑、美观。"
    },
    {
      "name": "工程塑料-ABS（黑色）",
      "category": "塑料",
      "code": "P29",
      "supported_finishes": [
        "喷油",
        "UV打印"
      ],
      "supported_tolerances": [
        "GB/T 1804-2000 m级",
        "±0.10mm",
        "±0.05mm"
      ],
      "supported_roughnesses": [
        "严格外观",
        "常规外观"
      ],
      "thickness_limit": {
        "min_mm": 1,
        "max_mm": 9999
      },
      "guidance": "黑色ABS不喷油表面容易有磨损划痕、泛白，喷油后表面更光滑、美观。"
    },
    {
      "name": "赛钢-POM（白色）",
      "category": "塑料",
      "code": "P31",
      "supported_finishes": [
        "UV打印"
      ],
      "supported_tolerances": [
        "GB/T 1804-2000 m级",
        "±0.10mm",
        "±0.05mm"
      ],
      "supported_roughnesses": [
        "常规外观",
        "严格外观"
      ],
      "thickness_limit": {
        "min_mm": 1,
        "max_mm": 9999
      },
      "guidance": ""
    },
    {
      "name": "赛钢-POM（黑色）",
      "category": "塑料",
      "code": "P13",
      "supported_finishes": [
        "UV打印"
      ],
      "supported_tolerances": [
        "GB/T 1804-2000 m级",
        "±0.10mm",
        "±0.05mm"
      ],
      "supported_roughnesses": [
        "常规外观",
        "严格外观"
      ],
      "thickness_limit": {
        "min_mm": 1,
        "max_mm": 9999
      },
      "guidance": ""
    },
    {
      "name": "电木（橘黄色）",
      "category": "塑料",
      "code": "P11",
      "supported_finishes": [
        "喷油",
        "UV打印"
      ],
      "supported_tolerances": [
        "GB/T 1804-2000 m级",
        "±0.10mm",
        "±0.05mm"
      ],
      "supported_roughnesses": [
        "严格外观",
        "常规外观"
      ],
      "thickness_limit": {
        "min_mm": 1,
        "max_mm": 999
      },
      "guidance": "电木不喷油，表面容易有划痕，材料表面泛白，喷油后表面光滑更美观。"
    },
    {
      "name": "电木（黑色）",
      "category": "塑料",
      "code": "P10",
      "supported_finishes": [
        "喷油",
        "UV打印"
      ],
      "supported_tolerances": [
        "GB/T 1804-2000 m级",
        "±0.10mm",
        "±0.05mm"
      ],
      "supported_roughnesses": [
        "严格外观",
        "常规外观"
      ],
      "thickness_limit": {
        "min_mm": 1,
        "max_mm": 60
      },
      "guidance": "电木不喷油，表面容易有划痕，材料表面泛白，喷油后表面光滑更美观。"
    },
    {
      "name": "亚克力",
      "category": "塑料",
      "code": "P17",
      "supported_finishes": [
        "UV打印",
        "仅喷砂",
        "透明抛光"
      ],
      "supported_tolerances": [
        "GB/T 1804-2000 m级",
        "±0.10mm",
        "±0.05mm"
      ],
      "supported_roughnesses": [
        "常规外观",
        "严格外观"
      ],
      "thickness_limit": {
        "min_mm": 1,
        "max_mm": 9999
      },
      "guidance": ""
    },
    {
      "name": "环氧板-FR4（绿色）",
      "category": "塑料",
      "code": "P63",
      "supported_finishes": [
        "UV打印"
      ],
      "supported_tolerances": [
        "GB/T 1804-2000 m级",
        "±0.10mm",
        "±0.05mm"
      ],
      "supported_roughnesses": [
        "常规外观",
        "严格外观"
      ],
      "thickness_limit": {
        "min_mm": 1,
        "max_mm": 9999
      },
      "guidance": ""
    },
    {
      "name": "尼龙-PA6（白色）",
      "category": "塑料",
      "code": "P24",
      "supported_finishes": [
        "UV打印"
      ],
      "supported_tolerances": [
        "GB/T 1804-2000 m级",
        "±0.10mm",
        "±0.05mm"
      ],
      "supported_roughnesses": [
        "常规外观",
        "严格外观"
      ],
      "thickness_limit": {
        "min_mm": 1,
        "max_mm": 9999
      },
      "guidance": ""
    },
    {
      "name": "聚碳酸酯-PC",
      "category": "塑料",
      "code": "P23",
      "supported_finishes": [
        "UV打印",
        "仅喷砂",
        "透明处理(蓝色)"
      ],
      "supported_tolerances": [
        "GB/T 1804-2000 m级",
        "±0.10mm",
        "±0.05mm"
      ],
      "supported_roughnesses": [
        "常规外观",
        "严格外观"
      ],
      "thickness_limit": {
        "min_mm": 1,
        "max_mm": 9999
      },
      "guidance": ""
    },
    {
      "name": "黄铜-H59",
      "category": "铜合金",
      "code": "U3",
      "supported_finishes": [
        "钝化",
        "激光打标",
        "仅喷砂",
        "镜面抛光"
      ],
      "supported_tolerances": [
        "GB/T 1804-2000 m级",
        "±0.10mm",
        "±0.05mm"
      ],
      "supported_roughnesses": [
        "严格外观",
        "常规外观"
      ],
      "thickness_limit": {
        "min_mm": 0.7,
        "max_mm": 9999.99
      },
      "guidance": "备注：铜件表面极易氧化，如未做钝化，收货后及时处理。"
    },
    {
      "name": "紫铜-T2",
      "category": "铜合金",
      "code": "U2",
      "supported_finishes": [
        "钝化",
        "激光打标",
        "仅喷砂",
        "镜面抛光"
      ],
      "supported_tolerances": [
        "GB/T 1804-2000 m级",
        "±0.10mm",
        "±0.05mm"
      ],
      "supported_roughnesses": [
        "严格外观",
        "常规外观"
      ],
      "thickness_limit": {
        "min_mm": 0.7,
        "max_mm": 9999.99
      },
      "guidance": "备注：铜件表面极易氧化，如未做钝化，收货后及时处理。"
    },
    {
      "name": "铝合金-6061",
      "category": "铝合金",
      "code": "A7",
      "supported_finishes": [
        "喷砂+普通阳极氧化",
        "喷砂+导电氧化",
        "喷砂+硬质阳极氧化",
        "激光打标",
        "拉丝",
        "UV打印",
        "仅喷砂",
        "普通阳极氧化(不喷砂)",
        "导电氧化(不喷砂)",
        "硬质阳极氧化(不喷砂)",
        "拉丝+普通阳极氧化"
      ],
      "supported_tolerances": [
        "±0.02mm",
        "GB/T 1804-2000 m级",
        "±0.10mm",
        "±0.05mm"
      ],
      "supported_roughnesses": [
        "严格外观",
        "常规外观",
        "极致外观"
      ],
      "thickness_limit": {
        "min_mm": 0.5,
        "max_mm": 9999.99
      },
      "guidance": "铝合金不喷砂有刀痕，同时选择阳极氧化处理能得到光饰效果，且耐磨，还可以选择需要的颜色，建议根据实际情况选择喷砂、氧化处理。"
    },
    {
      "name": "铝合金-7075",
      "category": "铝合金",
      "code": "A8",
      "supported_finishes": [
        "喷砂+普通阳极氧化",
        "喷砂+导电氧化",
        "喷砂+硬质阳极氧化",
        "激光打标",
        "拉丝",
        "UV打印",
        "仅喷砂",
        "普通阳极氧化(不喷砂)",
        "导电氧化(不喷砂)",
        "硬质阳极氧化(不喷砂)",
        "拉丝+普通阳极氧化"
      ],
      "supported_tolerances": [
        "±0.02mm",
        "GB/T 1804-2000 m级",
        "±0.10mm",
        "±0.05mm"
      ],
      "supported_roughnesses": [
        "严格外观",
        "常规外观",
        "极致外观"
      ],
      "thickness_limit": {
        "min_mm": 0.5,
        "max_mm": 9999.99
      },
      "guidance": "1.铝合金不喷砂有刀痕，同时选择阳极氧化处理能得到光饰效果，且耐磨，还可以选择需要的颜色，建议根据实际情况选择喷砂、氧化处理；2.铝合金-7075厚度超过50mm时，表面氧化除了黑色，其他颜色会有材料纹。"
    }
  ],
  "surface_finishes": [
    {
      "name": "激光打标",
      "category": "类别三",
      "code": "JGDB1",
      "requires_2d_drawing": true,
      "options": {
        "option_name": "图纸",
        "show_type": 0,
        "visible_flag": false,
        "items": [
          {
            "attribute_id": "14c6d2acf12f4aee91514a3ff0601a0d",
            "name": "请上传图纸",
            "code": "U1",
            "is_default": false,
            "gloss_options": [],
            "requires_drawing": true
          }
        ]
      },
      "remark": "备注：1.激光打标需上传2D图纸，格式支持DWG/DXF；备注：2.打标后会露出材料本色，成本低且牢固不易掉，但不支持选颜色。"
    },
    {
      "name": "镜面抛光",
      "category": "类别三",
      "code": "JMPG1",
      "requires_2d_drawing": false,
      "options": null,
      "remark": ""
    },
    {
      "name": "UV打印",
      "category": "类别三",
      "code": "SY1",
      "requires_2d_drawing": false,
      "options": {
        "option_name": "颜色",
        "show_type": 1,
        "visible_flag": true,
        "items": [
          {
            "attribute_id": "7d73e3f7e871491cadca118008fccc18",
            "name": "黑色",
            "code": "HS001",
            "is_default": true,
            "gloss_options": [
              "请上传图纸"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "0b47fa84a5b4458cbc458a7b964f0400",
            "name": "白色",
            "code": "BS001",
            "is_default": false,
            "gloss_options": [
              "请上传图纸"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "62a0d64827b94404bec467bd0fb9a86a",
            "name": "红色",
            "code": "2347C",
            "is_default": false,
            "gloss_options": [
              "请上传图纸"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "101e59759a754259aecec8fe4a9cbf17",
            "name": "橙色",
            "code": "C19",
            "is_default": false,
            "gloss_options": [
              "请上传图纸"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "ff98cbbaa1ca4582afd3ae661a175d25",
            "name": "黄色",
            "code": "3945C",
            "is_default": false,
            "gloss_options": [
              "请上传图纸"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "21a6396f95c842bcb0b8fa62be28ea97",
            "name": "绿色",
            "code": "802C",
            "is_default": false,
            "gloss_options": [
              "请上传图纸"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "97ac279a69214a4bb0ac68000bf569e9",
            "name": "青色",
            "code": "C20",
            "is_default": false,
            "gloss_options": [
              "请上传图纸"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "47d5a4ced095426f83d99ec53f12a45c",
            "name": "紫色",
            "code": "513C",
            "is_default": false,
            "gloss_options": [
              "请上传图纸"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "5430c1b24f1047e4b0c873c8c8228854",
            "name": "多色",
            "code": "DC2",
            "is_default": false,
            "gloss_options": [
              "请上传图纸"
            ],
            "requires_drawing": false
          }
        ]
      },
      "remark": "备注：1.UV打印需上传2D图纸，格式支持DWG/DXF，图案会凸起约等0.3mm，金属材料建议选用激光打标；备注：2.请按1:1的比例设计或把尺寸在图中标注，并注明颜色（不支持非平面印刷，支持单色、多彩色），示例如下："
    },
    {
      "name": "透明处理(蓝色)",
      "category": "类别二",
      "code": "34",
      "requires_2d_drawing": false,
      "options": null,
      "remark": ""
    },
    {
      "name": "钝化",
      "category": "类别二",
      "code": "DH1",
      "requires_2d_drawing": false,
      "options": null,
      "remark": ""
    },
    {
      "name": "普通阳极氧化(不喷砂)",
      "category": "类别二",
      "code": "H1",
      "requires_2d_drawing": false,
      "options": {
        "option_name": "颜色",
        "show_type": 1,
        "visible_flag": true,
        "items": [
          {
            "attribute_id": "5aeb31a407ff48a181eaf7bb713f0e05",
            "name": "本色",
            "code": "C1",
            "is_default": true,
            "gloss_options": [
              "哑光",
              "亮光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "1927f86e2f09419e8cee90cbeffde9ad",
            "name": "黑色",
            "code": "C2",
            "is_default": false,
            "gloss_options": [
              "哑光",
              "亮光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "ca81cfae3ce6455384a35f97a4eae25f",
            "name": "深空灰",
            "code": "C4",
            "is_default": false,
            "gloss_options": [
              "哑光",
              "亮光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "f0bd6492905f4bfe9a6c0803a90e2bd2",
            "name": "红色",
            "code": "C5",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "f07bd17e21d341fbb0eb82d9c85095bb",
            "name": "粉红色",
            "code": "C6",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "b937dd2eb61d42279b6ef1a0aecf29b5",
            "name": "天蓝色",
            "code": "C7",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "47f508c41e564261abf78228aeb29634",
            "name": "深绿色",
            "code": "C8",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "7cbac157b69d49ddbfd22b293a2f5199",
            "name": "沙金",
            "code": "C9",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "835feec0ef574f3fa964feda90395f61",
            "name": "宝蓝色",
            "code": "C18",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          }
        ]
      },
      "remark": "备注：1.不喷砂表面有刀痕，不美观，建议选择喷砂+普通阳极氧化；备注：2.哑光，表面反光率低，光线模糊不明显，光感柔和，不刺眼；亮光，表面反光效果好，反光度高，光线清晰明亮。"
    },
    {
      "name": "导电氧化(不喷砂)",
      "category": "类别二",
      "code": "H15",
      "requires_2d_drawing": false,
      "options": {
        "option_name": "颜色",
        "show_type": 1,
        "visible_flag": true,
        "items": [
          {
            "attribute_id": "296b70389021402aa984657bc2ab66c1",
            "name": "本色",
            "code": "C1",
            "is_default": true,
            "gloss_options": [],
            "requires_drawing": false
          }
        ]
      },
      "remark": "备注：1.不喷砂表面有刀痕，不美观，建议选择喷砂+导电氧化。"
    },
    {
      "name": "喷砂+普通阳极氧化",
      "category": "类别二",
      "code": "H21",
      "requires_2d_drawing": false,
      "options": {
        "option_name": "颜色",
        "show_type": 1,
        "visible_flag": true,
        "items": [
          {
            "attribute_id": "0e29e74b4f8c42ca984a0f76eb8a2792",
            "name": "本色",
            "code": "C1",
            "is_default": true,
            "gloss_options": [
              "哑光",
              "亮光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "e02eb2fc38ae4d1e978308959c4bfc8d",
            "name": "黑色",
            "code": "C2",
            "is_default": false,
            "gloss_options": [
              "哑光",
              "亮光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "401fbaae3fd04ca6b7380812dee17524",
            "name": "深空灰",
            "code": "C4",
            "is_default": false,
            "gloss_options": [
              "哑光",
              "亮光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "b8b7236b2e794302815fe9f374039859",
            "name": "红色",
            "code": "C5",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "c3d175972fbe4693bc8b5708c5bd8a58",
            "name": "粉红色",
            "code": "C6",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "91ea7339e4b147e4956feabefbb91df2",
            "name": "天蓝色",
            "code": "C7",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "6f42b04b4300458d81aa64d641ddbbdc",
            "name": "深绿色",
            "code": "C8",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "a5e67a907f6c47769bb84d757794255d",
            "name": "沙金",
            "code": "C9",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "9d69522ceb2449bca68696eabd06dfbb",
            "name": "宝蓝色",
            "code": "C18",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          }
        ]
      },
      "remark": "备注：1.哑光，表面反光率低，光线模糊不明显，光感柔和，不刺眼；亮光，表面反光效果好，反光度高；备注：2.喷砂默认统一按100目进行处理。"
    },
    {
      "name": "喷砂+硬质阳极氧化",
      "category": "类别二",
      "code": "H22",
      "requires_2d_drawing": false,
      "options": {
        "option_name": "颜色",
        "show_type": 1,
        "visible_flag": true,
        "items": [
          {
            "attribute_id": "1e6f6ab6dda64927b182103b3675e38d",
            "name": "本色",
            "code": "C1",
            "is_default": true,
            "gloss_options": [],
            "requires_drawing": false
          },
          {
            "attribute_id": "2a57938df28a44c1b1eca22dcea04540",
            "name": "黑色",
            "code": "C2",
            "is_default": false,
            "gloss_options": [],
            "requires_drawing": false
          }
        ]
      },
      "remark": "备注：喷砂默认统一按100目进行处理，硬质氧化 - 本色偏暗金色。"
    },
    {
      "name": "喷砂+导电氧化",
      "category": "类别二",
      "code": "H23",
      "requires_2d_drawing": false,
      "options": {
        "option_name": "颜色",
        "show_type": 1,
        "visible_flag": true,
        "items": [
          {
            "attribute_id": "5ab30ac549f948bd82b3913bc8fa87e4",
            "name": "本色",
            "code": "C1",
            "is_default": false,
            "gloss_options": [],
            "requires_drawing": false
          }
        ]
      },
      "remark": "备注：喷砂默认统一按100目进行处理。"
    },
    {
      "name": "拉丝+普通阳极氧化",
      "category": "类别二",
      "code": "H24",
      "requires_2d_drawing": false,
      "options": {
        "option_name": "颜色",
        "show_type": 1,
        "visible_flag": true,
        "items": [
          {
            "attribute_id": "5847809316eb4c65a066d8ba4bc8fd05",
            "name": "本色",
            "code": "C1",
            "is_default": true,
            "gloss_options": [
              "哑光",
              "亮光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "7e9020e9c14b4b88aebd23dc6461190f",
            "name": "黑色",
            "code": "C2",
            "is_default": false,
            "gloss_options": [
              "哑光",
              "亮光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "892f6e431d6e4bb4b412438a94a136f1",
            "name": "深空灰",
            "code": "C4",
            "is_default": false,
            "gloss_options": [
              "哑光",
              "亮光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "59f671c3cf5e4b8e8614b41f9e1bebcd",
            "name": "红色",
            "code": "C5",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "bdb9a73da0084fb28b968ce77ffe4581",
            "name": "粉红色",
            "code": "C6",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "d327a7fbd6294a288f488a051c6d9520",
            "name": "天蓝色",
            "code": "C7",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "eaffd84a859a44539521a6aaff664b4c",
            "name": "深绿色",
            "code": "C8",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "39031d2278a0461b86e34c64070dc86d",
            "name": "沙金",
            "code": "C9",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "64025f193bb240ea9a13cea4b49b1d47",
            "name": "宝蓝色",
            "code": "C18",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          }
        ]
      },
      "remark": "备注：1.哑光，表面反光率低，光线模糊不明显，光感柔和，不刺眼；亮光，表面反光效果好，反光度高；备注：2.只支持板类平面件（限1000*360mm），异型件圆弧面或台阶面无法进行拉丝处理。"
    },
    {
      "name": "硬质阳极氧化(不喷砂)",
      "category": "类别二",
      "code": "H3",
      "requires_2d_drawing": false,
      "options": {
        "option_name": "颜色",
        "show_type": 1,
        "visible_flag": true,
        "items": [
          {
            "attribute_id": "f89a6125ae394565a37c2d6b6a37a084",
            "name": "本色",
            "code": "C1",
            "is_default": true,
            "gloss_options": [],
            "requires_drawing": false
          },
          {
            "attribute_id": "d02b0efa67fe404ea41cbb087aab4a39",
            "name": "黑色",
            "code": "C2",
            "is_default": false,
            "gloss_options": [],
            "requires_drawing": false
          }
        ]
      },
      "remark": "备注：不喷砂表面有刀痕，不美观，建议选择喷砂+硬质阳极氧化。"
    },
    {
      "name": "喷油",
      "category": "类别二",
      "code": "PY1",
      "requires_2d_drawing": false,
      "options": {
        "option_name": "颜色",
        "show_type": 1,
        "visible_flag": true,
        "items": [
          {
            "attribute_id": "53adf10118b047c1ad2b4b3952c56aba",
            "name": "黑色",
            "code": "HS001",
            "is_default": true,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          },
          {
            "attribute_id": "d4d84ded80794f14b1eb035a605d9ad6",
            "name": "白色",
            "code": "BS001",
            "is_default": false,
            "gloss_options": [
              "哑光"
            ],
            "requires_drawing": false
          }
        ]
      },
      "remark": ""
    },
    {
      "name": "透明抛光",
      "category": "类别二",
      "code": "TMPG1",
      "requires_2d_drawing": false,
      "options": null,
      "remark": ""
    },
    {
      "name": "拉丝",
      "category": "类别二",
      "code": "X3",
      "requires_2d_drawing": false,
      "options": null,
      "remark": "备注：只支持板类平面件（限1000*360mm），异型件圆弧面或台阶面无法进行拉丝处理。"
    },
    {
      "name": "仅喷砂",
      "category": "类别二",
      "code": "X7",
      "requires_2d_drawing": false,
      "options": null,
      "remark": "备注：铝合金不喷砂有刀痕，默认统一按100目进行喷砂。"
    },
    {
      "name": "镀镍",
      "category": "类别四",
      "code": "DL1",
      "requires_2d_drawing": false,
      "options": null,
      "remark": ""
    },
    {
      "name": "发黑",
      "category": "类别四",
      "code": "FH1",
      "requires_2d_drawing": false,
      "options": null,
      "remark": ""
    }
  ],
  "tolerances": [
    {
      "name": "GB/T 1804-2000 m级",
      "is_default": true,
      "requires_2d_drawing": false
    },
    {
      "name": "±0.10mm",
      "is_default": false,
      "requires_2d_drawing": false
    },
    {
      "name": "±0.05mm",
      "is_default": false,
      "requires_2d_drawing": true
    },
    {
      "name": "±0.02mm",
      "is_default": false,
      "requires_2d_drawing": true
    }
  ],
  "roughnesses": [
    {
      "name": "常规外观",
      "is_default": true,
      "requires_2d_drawing": false
    },
    {
      "name": "严格外观",
      "is_default": false,
      "requires_2d_drawing": true
    },
    {
      "name": "极致外观",
      "is_default": false,
      "requires_2d_drawing": true
    }
  ],
  "inspections": [
    {
      "name": "不需要",
      "is_default": true
    },
    {
      "name": "需要",
      "is_default": false
    }
  ],
  "delivery_tiers": [
    {
      "name": "加急交期",
      "code": "UD",
      "is_default": false
    },
    {
      "name": "标准交期",
      "code": "BD",
      "is_default": true
    },
    {
      "name": "经济交期",
      "code": "ED",
      "is_default": false
    }
  ]
};

/** Xometry US 内置参数与约束元数据 */
export const XOM_DEFAULT_CATALOG = {
  "subprocesses": [
    {
      "name": "No Preference",
      "code": "NO_PREFERENCE",
      "is_default": true
    },
    {
      "name": "CNC Mill and Turning Combo",
      "code": "MILL_TURN_COMBO",
      "is_default": false
    },
    {
      "name": "CNC Milling",
      "code": "MILLING",
      "is_default": false
    },
    {
      "name": "CNC Router",
      "code": "ROUTER",
      "is_default": false
    },
    {
      "name": "CNC Turning (Lathe)",
      "code": "TURNING",
      "is_default": false
    },
    {
      "name": "Micro Machining",
      "code": "MICRO_MACHINING",
      "is_default": false
    },
    {
      "name": "Swiss-Type Turning",
      "code": "SWISS_TURNING",
      "is_default": false
    },
    {
      "name": "Other",
      "code": "OTHER",
      "is_default": false
    }
  ],
  "material_categories": [
    "Aluminum",
    "Stainless Steel",
    "Steel",
    "Brass, Bronze, or Copper",
    "Plastic",
    "Titanium",
    "Composite",
    "Other"
  ],
  "materials": [
    {
      "name": "Aluminum 2024",
      "category": "Aluminum",
      "is_metal": true,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Black Anodize",
        "Black Hardcoat Anodize",
        "Blue Anodize",
        "Clear Anodize",
        "Clear Hardcoat Anodize",
        "Gold Anodize",
        "Gray Hardcoat Anodize",
        "Green Anodize",
        "Orange Anodize",
        "PTFE Impregnated Hard Anodize",
        "Purple Anodize",
        "Red Anodize",
        "Yellow Anodize",
        "Chem Film Clear",
        "Chem Film Gold",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A high-strength, aerospace-grade aluminum alloy known for its excellent fatigue resistance and machinability. Not as corrosion-resistant as 6061 but ideal for aerospace and structural applications."
    },
    {
      "name": "Aluminum 6061-T6x (Best Available)",
      "category": "Aluminum",
      "is_metal": true,
      "cost_tier": "Cost tier 1 of 5",
      "supported_finishes": [
        "Standard",
        "Black Anodize",
        "Black Hardcoat Anodize",
        "Blue Anodize",
        "Clear Anodize",
        "Clear Hardcoat Anodize",
        "Gold Anodize",
        "Gray Hardcoat Anodize",
        "Green Anodize",
        "Orange Anodize",
        "PTFE Impregnated Hard Anodize",
        "Purple Anodize",
        "Red Anodize",
        "Yellow Anodize",
        "Chem Film Clear",
        "Chem Film Gold",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A versatile, heat-treatable aluminum alloy with excellent corrosion resistance and a good strength-to-weight ratio. Allows for flexibility when any variation of 6061-T6-tempered alloys is acceptable."
    },
    {
      "name": "Aluminum 6061-T651, Plate",
      "category": "Aluminum",
      "is_metal": true,
      "cost_tier": "Cost tier 1 of 5",
      "supported_finishes": [
        "Standard",
        "Black Anodize",
        "Black Hardcoat Anodize",
        "Blue Anodize",
        "Clear Anodize",
        "Clear Hardcoat Anodize",
        "Gold Anodize",
        "Gray Hardcoat Anodize",
        "Green Anodize",
        "Orange Anodize",
        "PTFE Impregnated Hard Anodize",
        "Purple Anodize",
        "Red Anodize",
        "Yellow Anodize",
        "Chem Film Clear",
        "Chem Film Gold",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A stress-relieved aluminum plate variant of 6061-T6, providing excellent machinability, corrosion resistance, and mechanical properties for structural and aerospace applications."
    },
    {
      "name": "Aluminum 6061-T6/T6511, Bar/Rod",
      "category": "Aluminum",
      "is_metal": true,
      "cost_tier": "Cost tier 1 of 5",
      "supported_finishes": [
        "Standard",
        "Black Anodize",
        "Black Hardcoat Anodize",
        "Blue Anodize",
        "Clear Anodize",
        "Clear Hardcoat Anodize",
        "Gold Anodize",
        "Gray Hardcoat Anodize",
        "Green Anodize",
        "Orange Anodize",
        "PTFE Impregnated Hard Anodize",
        "Purple Anodize",
        "Red Anodize",
        "Yellow Anodize",
        "Chem Film Clear",
        "Chem Film Gold",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "An extruded aluminum bar/rod version of 6061-T6 with high strength, good corrosion resistance, and excellent machinability, commonly used in aerospace and industrial components."
    },
    {
      "name": "Aluminum 6063",
      "category": "Aluminum",
      "is_metal": true,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Black Anodize",
        "Black Hardcoat Anodize",
        "Blue Anodize",
        "Clear Anodize",
        "Clear Hardcoat Anodize",
        "Gold Anodize",
        "Gray Hardcoat Anodize",
        "Green Anodize",
        "Orange Anodize",
        "PTFE Impregnated Hard Anodize",
        "Purple Anodize",
        "Red Anodize",
        "Yellow Anodize",
        "Chem Film Clear",
        "Chem Film Gold",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A medium-strength aluminum alloy known for its superior corrosion resistance and smooth surface finish, commonly used in architectural and structural applications."
    },
    {
      "name": "Aluminum 7050",
      "category": "Aluminum",
      "is_metal": true,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Black Anodize",
        "Black Hardcoat Anodize",
        "Blue Anodize",
        "Clear Anodize",
        "Clear Hardcoat Anodize",
        "Gold Anodize",
        "Gray Hardcoat Anodize",
        "Green Anodize",
        "Orange Anodize",
        "PTFE Impregnated Hard Anodize",
        "Purple Anodize",
        "Red Anodize",
        "Yellow Anodize",
        "Chem Film Clear",
        "Chem Film Gold",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A high-strength aluminum alloy with excellent resistance to stress corrosion cracking, commonly used in aerospace and structural applications where toughness is required."
    },
    {
      "name": "Aluminum 7075-T6",
      "category": "Aluminum",
      "is_metal": true,
      "cost_tier": "Cost tier 1 of 5",
      "supported_finishes": [
        "Standard",
        "Black Anodize",
        "Black Hardcoat Anodize",
        "Blue Anodize",
        "Clear Anodize",
        "Clear Hardcoat Anodize",
        "Gold Anodize",
        "Gray Hardcoat Anodize",
        "Green Anodize",
        "Orange Anodize",
        "PTFE Impregnated Hard Anodize",
        "Purple Anodize",
        "Red Anodize",
        "Yellow Anodize",
        "Chem Film Clear",
        "Chem Film Gold",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "One of the strongest aluminum alloys, offering high strength-to-weight ratio and excellent fatigue resistance, widely used in aerospace and high-performance applications."
    },
    {
      "name": "Aluminum 7075-T7351",
      "category": "Aluminum",
      "is_metal": true,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Black Anodize",
        "Black Hardcoat Anodize",
        "Blue Anodize",
        "Clear Anodize",
        "Clear Hardcoat Anodize",
        "Gold Anodize",
        "Gray Hardcoat Anodize",
        "Green Anodize",
        "Orange Anodize",
        "PTFE Impregnated Hard Anodize",
        "Purple Anodize",
        "Red Anodize",
        "Yellow Anodize",
        "Chem Film Clear",
        "Chem Film Gold",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A stress-relieved version of 7075-T6, offering improved fracture toughness and resistance to stress corrosion cracking while maintaining high strength."
    },
    {
      "name": "Aluminum MIC-6",
      "category": "Aluminum",
      "is_metal": true,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Black Anodize",
        "Black Hardcoat Anodize",
        "Blue Anodize",
        "Clear Anodize",
        "Clear Hardcoat Anodize",
        "Gold Anodize",
        "Gray Hardcoat Anodize",
        "Green Anodize",
        "Orange Anodize",
        "PTFE Impregnated Hard Anodize",
        "Purple Anodize",
        "Red Anodize",
        "Yellow Anodize",
        "Chem Film Clear",
        "Chem Film Gold",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A precision-machined cast aluminum plate known for its excellent stability, flatness, and uniformity, making it ideal for tooling, jigs, and fixtures."
    },
    {
      "name": "Copper 101",
      "category": "Brass, Bronze, or Copper",
      "is_metal": true,
      "cost_tier": "Cost tier 3 of 5",
      "supported_finishes": [
        "Standard",
        "Passivate",
        "Temper",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A high-purity copper alloy (99.99% Cu) with excellent electrical and thermal conductivity, commonly used in electrical and electronic applications."
    },
    {
      "name": "Copper 260 (Brass)",
      "category": "Brass, Bronze, or Copper",
      "is_metal": true,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Passivate",
        "Temper",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A brass alloy composed of copper and zinc, offering good corrosion resistance, machinability, and formability, often used in decorative and functional applications."
    },
    {
      "name": "Copper C110",
      "category": "Brass, Bronze, or Copper",
      "is_metal": true,
      "cost_tier": "Cost tier 4 of 5",
      "supported_finishes": [
        "Standard",
        "Passivate",
        "Temper",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A widely used high-conductivity copper alloy (99.9% Cu) known for its excellent electrical and thermal properties, used in wiring, bus bars, and heat exchangers."
    },
    {
      "name": "Copper C932 (Bronze)",
      "category": "Brass, Bronze, or Copper",
      "is_metal": true,
      "cost_tier": "Cost tier 3 of 5",
      "supported_finishes": [
        "Standard",
        "Passivate",
        "Temper",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A leaded tin bronze alloy with excellent wear resistance and self-lubricating properties, commonly used in bearings and bushings."
    },
    {
      "name": "Copper C360 (Brass)",
      "category": "Brass, Bronze, or Copper",
      "is_metal": true,
      "cost_tier": "Cost tier 3 of 5",
      "supported_finishes": [
        "Standard",
        "Passivate",
        "Temper",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A free-machining brass alloy with excellent machinability, moderate strength, and corrosion resistance, widely used in precision components."
    },
    {
      "name": "Garolite G10 (FR4)",
      "category": "Composite",
      "is_metal": false,
      "cost_tier": "Cost tier 3 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A fiberglass-reinforced epoxy laminate with excellent electrical insulation, mechanical strength, and flame resistance, commonly used in electrical and structural applications."
    },
    {
      "name": "Garolite G10",
      "category": "Composite",
      "is_metal": false,
      "cost_tier": "Cost tier 3 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A high-performance composite material made from fiberglass and epoxy resin, offering excellent mechanical strength, low moisture absorption, and electrical insulation properties."
    },
    {
      "name": "Garolite G11 (FR5)",
      "category": "Composite",
      "is_metal": false,
      "cost_tier": "Cost tier 3 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A high-strength fiberglass laminate similar to G10 but with better heat resistance and electrical insulating properties, often used in demanding industrial applications."
    },
    {
      "name": "ABS",
      "category": "Plastic",
      "is_metal": false,
      "cost_tier": "Cost tier 1 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A tough, impact-resistant plastic with good machinability, commonly used in prototyping, automotive, and consumer products."
    },
    {
      "name": "Acrylic",
      "category": "Plastic",
      "is_metal": false,
      "cost_tier": "Cost tier 1 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A transparent thermoplastic with excellent optical clarity, weather resistance, and moderate impact strength, often used in displays and enclosures."
    },
    {
      "name": "Acetal (POM)",
      "category": "Plastic",
      "is_metal": false,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A low-friction engineering plastic with high impact resistance and excellent dimensional stability, making it ideal for gears, bearings, and precision parts. Acetal is the generic version of Delrin."
    },
    {
      "name": "Delrin 100 (AF)",
      "category": "Plastic",
      "is_metal": false,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A specialized grade of Delrin with added PTFE for improved wear resistance and lower friction, ideal for high-performance sliding applications."
    },
    {
      "name": "Delrin 150",
      "category": "Plastic",
      "is_metal": false,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A general-purpose acetal homopolymer offering high strength, low friction, and excellent machinability for precision components."
    },
    {
      "name": "HDPE",
      "category": "Plastic",
      "is_metal": false,
      "cost_tier": "Cost tier 1 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A lightweight, impact-resistant plastic with good chemical resistance, used in industrial, outdoor, marine, and food applications."
    },
    {
      "name": "Nylon 6/6",
      "category": "Plastic",
      "is_metal": false,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A strong, wear-resistant plastic with good mechanical properties, commonly used for gears, bushings, and structural components."
    },
    {
      "name": "PC (Polycarbonate)",
      "category": "Plastic",
      "is_metal": false,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A tough, impact-resistant plastic with excellent transparency and heat resistance, commonly used in protective covers and optical applications."
    },
    {
      "name": "PEEK",
      "category": "Plastic",
      "is_metal": false,
      "cost_tier": "Cost tier 4 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A high-performance thermoplastic with exceptional mechanical strength, chemical resistance, and heat resistance, used in aerospace and medical applications."
    },
    {
      "name": "PEEK (USP Class VI TECAPEEK)",
      "category": "Plastic",
      "is_metal": false,
      "cost_tier": "Cost tier 4 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A biocompatible grade of PEEK meeting USP Class VI standards, suitable for medical and pharmaceutical applications."
    },
    {
      "name": "PEEK GF30",
      "category": "Plastic",
      "is_metal": false,
      "cost_tier": "Cost tier 4 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A glass-filled PEEK composite with enhanced stiffness, strength, and wear resistance for high-load applications."
    },
    {
      "name": "Polypropylene",
      "category": "Plastic",
      "is_metal": false,
      "cost_tier": "Cost tier 3 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A lightweight, flexible plastic with good chemical resistance, impact strength, and low moisture absorption, often used in containers and industrial applications."
    },
    {
      "name": "PTFE (Teflon)",
      "category": "Plastic",
      "is_metal": false,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A non-stick, chemically resistant plastic with excellent electrical insulation and low friction properties, ideal for seals, gaskets, and bearings."
    },
    {
      "name": "PVC",
      "category": "Plastic",
      "is_metal": false,
      "cost_tier": "Cost tier 1 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A rigid plastic with good chemical resistance, flame retardance, and electrical insulation properties, used in piping and industrial applications."
    },
    {
      "name": "UHMW PE",
      "category": "Plastic",
      "is_metal": false,
      "cost_tier": "Cost tier 1 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A highly durable polyethylene plastic with excellent wear resistance, impact strength, and low friction, commonly used in conveyor systems and impact surfaces."
    },
    {
      "name": "ULTEM 1000",
      "category": "Plastic",
      "is_metal": false,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A high-performance thermoplastic with excellent heat resistance, mechanical strength, and electrical properties, used in aerospace and electronics."
    },
    {
      "name": "ULTEM 2300",
      "category": "Plastic",
      "is_metal": false,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A 30% glass-filled ULTEM variant with enhanced stiffness and dimensional stability for demanding structural applications."
    },
    {
      "name": "Nitronic 60",
      "category": "Stainless Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 3 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Passivate",
        "Annealing",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A stainless steel alloy known for its excellent wear and galling resistance, commonly used in high-stress and sliding applications."
    },
    {
      "name": "Stainless Steel 15-5",
      "category": "Stainless Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 4 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Passivate",
        "Annealing",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A precipitation-hardened stainless steel with high strength and moderate corrosion resistance, used in aerospace and structural applications."
    },
    {
      "name": "Stainless Steel 15-5PH H1150",
      "category": "Stainless Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 4 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Passivate",
        "Annealing",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A heat-treated version of 15-5 stainless steel with improved toughness and stress resistance."
    },
    {
      "name": "Stainless Steel 15-5PH H900",
      "category": "Stainless Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 4 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Passivate",
        "Annealing",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A high-strength, precipitation-hardened stainless steel with good corrosion resistance, commonly used in aerospace components."
    },
    {
      "name": "Stainless Steel 17-4",
      "category": "Stainless Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 4 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Passivate",
        "Annealing",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A versatile, high-strength stainless steel with good corrosion resistance, commonly used in aerospace and medical applications."
    },
    {
      "name": "Stainless Steel 17-4PH H1150",
      "category": "Stainless Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 4 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Passivate",
        "Annealing",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A heat-treated version of 17-4 stainless steel offering improved toughness and corrosion resistance."
    },
    {
      "name": "Stainless Steel 17-4PH H900",
      "category": "Stainless Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 4 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Passivate",
        "Annealing",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A high-strength precipitation-hardened stainless steel with excellent fatigue resistance, used in demanding applications."
    },
    {
      "name": "Stainless Steel 303",
      "category": "Stainless Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 3 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Passivate",
        "Annealing",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "An easy-to-machine stainless steel with moderate corrosion resistance, commonly used in fasteners and fittings."
    },
    {
      "name": "Stainless Steel 304/304L",
      "category": "Stainless Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 4 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Passivate",
        "Annealing",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A widely used stainless steel with good corrosion resistance and formability, commonly used in food, medical, and industrial applications."
    },
    {
      "name": "Stainless Steel 316/316L",
      "category": "Stainless Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 4 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Passivate",
        "Annealing",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A corrosion-resistant stainless steel with superior resistance to marine and chemical environments."
    },
    {
      "name": "Next Available Stainless Steel 303, 304, or 316",
      "category": "Stainless Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Passivate",
        "Annealing",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A flexible option for sourcing the best available 300-series stainless steel with suitable machinability and corrosion resistance."
    },
    {
      "name": "Stainless Steel 410",
      "category": "Stainless Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 4 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Passivate",
        "Annealing",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A hardenable stainless steel with good wear resistance, commonly used in cutlery and industrial components."
    },
    {
      "name": "Stainless Steel 416",
      "category": "Stainless Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 4 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Passivate",
        "Annealing",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A free-machining stainless steel with high strength and moderate corrosion resistance, used in precision components."
    },
    {
      "name": "Stainless Steel 420",
      "category": "Stainless Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 4 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Passivate",
        "Annealing",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A high-hardness stainless steel with good corrosion resistance, often used in surgical instruments and cutlery."
    },
    {
      "name": "Stainless Steel 440C",
      "category": "Stainless Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 4 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Passivate",
        "Annealing",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Electropolish",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A high-carbon stainless steel with excellent wear resistance and hardness, used in bearings and blades."
    },
    {
      "name": "Steel 1018",
      "category": "Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Annealing",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A low-carbon steel with good weldability and machinability, commonly used in general-purpose applications."
    },
    {
      "name": "Steel 1215",
      "category": "Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 3 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Annealing",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A free-machining carbon steel with high machinability, used in precision components and fasteners."
    },
    {
      "name": "Steel 4130",
      "category": "Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 3 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Annealing",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A chromium-molybdenum (chromoly) alloy steel with good strength, toughness, and weldability, used in aerospace and automotive applications."
    },
    {
      "name": "Steel 4140",
      "category": "Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 3 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Annealing",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A high-strength alloy steel with excellent wear resistance, used in structural and mechanical applications."
    },
    {
      "name": "Steel 4140PH",
      "category": "Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 3 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Annealing",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A pre-hardened version of 4140 steel with improved toughness and machinability."
    },
    {
      "name": "Steel 4340",
      "category": "Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 4 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Annealing",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A high-strength, tough alloy steel with excellent fatigue resistance, commonly used in aerospace applications."
    },
    {
      "name": "Steel A36",
      "category": "Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Annealing",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A low-carbon structural steel with good weldability and machinability, used in construction and general fabrication."
    },
    {
      "name": "Tool Steel A2",
      "category": "Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Annealing",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "An air-hardening tool steel with high wear resistance and toughness, used for dies and punches."
    },
    {
      "name": "Tool Steel O1",
      "category": "Steel",
      "is_metal": true,
      "cost_tier": "Cost tier 2 of 5",
      "supported_finishes": [
        "Standard",
        "Black Oxide",
        "Annealing",
        "Case Harden",
        "Temper",
        "Through Harden",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "An oil-hardening tool steel with good toughness and machinability, commonly used in cutting tools."
    },
    {
      "name": "Titanium Grade 2",
      "category": "Titanium",
      "is_metal": true,
      "cost_tier": "Cost tier 5 of 5",
      "supported_finishes": [
        "Standard",
        "Titanium Anodize",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A commercially pure titanium, CPTi, with excellent corrosion resistance and moderate strength, used in marine and medical applications."
    },
    {
      "name": "Titanium Grade 5",
      "category": "Titanium",
      "is_metal": true,
      "cost_tier": "Cost tier 5 of 5",
      "supported_finishes": [
        "Standard",
        "Titanium Anodize",
        "Bead Blast",
        "Tumbled",
        "Electroless Nickel Plating",
        "Gold Plating",
        "Silver Plating",
        "Zinc Plating",
        "Cerakote",
        "Powder Coating",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "A high-strength titanium alloy, Ti-6Al-4V, with excellent corrosion resistance and lightweight properties, widely used in aerospace and biomedical industries."
    },
    {
      "name": "Other (Metal)",
      "category": "Other",
      "is_metal": true,
      "cost_tier": "Custom",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.005″ (±0.13mm)",
        "±.010″ (±0.25mm)",
        "This part requires tolerances tighter than ±.005″ (±0.13mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "Custom metal material to be specified in 2D engineering drawings or notes."
    },
    {
      "name": "Other (Plastic)",
      "category": "Other",
      "is_metal": false,
      "cost_tier": "Custom",
      "supported_finishes": [
        "Standard",
        "Bead Blast",
        "Request finish"
      ],
      "supported_tolerances": [
        "±.010″ (±0.25mm)",
        "±.020″ (±0.5mm)",
        "This part requires tolerances tighter than ±.010″ (±0.25mm)"
      ],
      "supported_roughnesses": [
        "125uin/3.2um Ra",
        "63uin/1.6um Ra",
        "32uin/0.8um Ra",
        "16uin/0.4um Ra"
      ],
      "description": "Custom polymer or composite material to be specified in 2D engineering drawings or notes."
    }
  ],
  "surface_finishes": [
    {
      "name": "Standard",
      "category": "Standard",
      "requires_2d_drawing": false,
      "description": "Standard as-milled finish. Cutters leave visible tool marks. Surface roughness held to 125uin/3.2um Ra unless specified."
    },
    {
      "name": "Black Anodize",
      "category": "Anodize",
      "requires_2d_drawing": false,
      "description": "Sulfuric acid anodizing (Type II) offering corrosion resistance and matte/gloss black appearance."
    },
    {
      "name": "Black Hardcoat Anodize",
      "category": "Anodize",
      "requires_2d_drawing": false,
      "description": "Hardcoat anodizing (Type III) providing dense, wear-resistant thick ceramic coating in black."
    },
    {
      "name": "Blue Anodize",
      "category": "Anodize",
      "requires_2d_drawing": false,
      "description": "Type II anodize dyed vibrant blue."
    },
    {
      "name": "Clear Anodize",
      "category": "Anodize",
      "requires_2d_drawing": false,
      "description": "Type II anodize without dye, retaining natural silver metallic appearance with enhanced corrosion resistance."
    },
    {
      "name": "Clear Hardcoat Anodize",
      "category": "Anodize",
      "requires_2d_drawing": false,
      "description": "Type III hardcoat anodize with superior wear resistance in natural/clear tone."
    },
    {
      "name": "Gold Anodize",
      "category": "Anodize",
      "requires_2d_drawing": false,
      "description": "Type II anodize dyed gold."
    },
    {
      "name": "Gray Hardcoat Anodize",
      "category": "Anodize",
      "requires_2d_drawing": false,
      "description": "Type III hardcoat anodize with matte gray appearance for heavy duty industrial use."
    },
    {
      "name": "Green Anodize",
      "category": "Anodize",
      "requires_2d_drawing": false,
      "description": "Type II anodize dyed green."
    },
    {
      "name": "Orange Anodize",
      "category": "Anodize",
      "requires_2d_drawing": false,
      "description": "Type II anodize dyed orange."
    },
    {
      "name": "PTFE Impregnated Hard Anodize",
      "category": "Anodize",
      "requires_2d_drawing": false,
      "description": "Type III hardcoat anodize sealed with PTFE particles for ultra-low friction and high abrasion resistance."
    },
    {
      "name": "Purple Anodize",
      "category": "Anodize",
      "requires_2d_drawing": false,
      "description": "Type II anodize dyed purple."
    },
    {
      "name": "Red Anodize",
      "category": "Anodize",
      "requires_2d_drawing": false,
      "description": "Type II anodize dyed red."
    },
    {
      "name": "Yellow Anodize",
      "category": "Anodize",
      "requires_2d_drawing": false,
      "description": "Type II anodize dyed yellow."
    },
    {
      "name": "Titanium Anodize",
      "category": "Anodize",
      "requires_2d_drawing": false,
      "description": "Electrolytic passivation of titanium for color coding, biocompatibility, and anti-galling."
    },
    {
      "name": "Chem Film Clear",
      "category": "Chemical Conversion",
      "requires_2d_drawing": false,
      "description": "Chromate conversion coating (MIL-DTL-5541 Type II Class 3) preserving conductivity and corrosion resistance."
    },
    {
      "name": "Chem Film Gold",
      "category": "Chemical Conversion",
      "requires_2d_drawing": false,
      "description": "Hexavalent or trivalent chromate conversion coating (Class 1A) providing corrosion protection and primer base."
    },
    {
      "name": "Black Oxide",
      "category": "Chemical Conversion",
      "requires_2d_drawing": false,
      "description": "Chemical conversion coating for steel and stainless steel offering mild corrosion resistance and black aesthetic."
    },
    {
      "name": "Passivate",
      "category": "Chemical Conversion",
      "requires_2d_drawing": false,
      "description": "Chemical passivation (ASTM A967) for stainless steel and copper alloys, removing free iron and forming oxide barrier."
    },
    {
      "name": "Annealing",
      "category": "Heat Treatments",
      "requires_2d_drawing": false,
      "description": "Heat treatment altering microstructure to reduce hardness, increase ductility and eliminate internal residual stresses."
    },
    {
      "name": "Case Harden",
      "category": "Heat Treatments",
      "requires_2d_drawing": false,
      "description": "Carburizing or nitriding to harden surface layer while retaining tough, ductile core."
    },
    {
      "name": "Temper",
      "category": "Heat Treatments",
      "requires_2d_drawing": false,
      "description": "Low-temperature thermal processing following quenching to achieve desired toughness and hardness balance."
    },
    {
      "name": "Through Harden",
      "category": "Heat Treatments",
      "requires_2d_drawing": false,
      "description": "Thermal hardening throughout the entire workpiece cross-section."
    },
    {
      "name": "Bead Blast",
      "category": "Mechanical Finishing",
      "requires_2d_drawing": false,
      "description": "Fine glass bead blasting yielding a uniform, non-directional satin or matte textured finish."
    },
    {
      "name": "Tumbled",
      "category": "Mechanical Finishing",
      "requires_2d_drawing": false,
      "description": "Vibratory or centrifugal barrel tumbling to break sharp edges, deburr, and smooth part surfaces."
    },
    {
      "name": "Electroless Nickel Plating",
      "category": "Plating",
      "requires_2d_drawing": false,
      "description": "Autocatalytic chemical deposition of nickel-phosphorus alloy offering uniform thickness on complex geometry."
    },
    {
      "name": "Gold Plating",
      "category": "Plating",
      "requires_2d_drawing": false,
      "description": "Electroplated gold layer for high-end electrical contacts, corrosion immunity, and solderability."
    },
    {
      "name": "Silver Plating",
      "category": "Plating",
      "requires_2d_drawing": false,
      "description": "Electroplated silver layer providing high electrical and thermal conductivity."
    },
    {
      "name": "Zinc Plating",
      "category": "Plating",
      "requires_2d_drawing": false,
      "description": "Sacrificial electroplated zinc barrier for ferrous components preventing atmospheric corrosion."
    },
    {
      "name": "Electropolish",
      "category": "Other",
      "requires_2d_drawing": false,
      "description": "Electrochemical deburring and micro-smoothing yielding brilliant mirror-like passive surface on stainless steel and copper."
    },
    {
      "name": "Cerakote",
      "category": "Other",
      "requires_2d_drawing": false,
      "description": "Polymer-ceramic composite coating providing extreme corrosion, abrasion, and chemical resistance."
    },
    {
      "name": "Powder Coating",
      "category": "Other",
      "requires_2d_drawing": false,
      "description": "Electrostatic dry powder application baked to a durable, decorative protective skin."
    },
    {
      "name": "Request finish",
      "category": "Other",
      "requires_2d_drawing": true,
      "description": "Custom surface treatment not listed above; requires specification details and 2D drawing."
    }
  ],
  "tolerances": [
    {
      "name": "±.005″ (±0.13mm)",
      "applicable_group": "metal",
      "is_default": true,
      "requires_2d_drawing": false
    },
    {
      "name": "±.010″ (±0.25mm)",
      "applicable_group": "metal",
      "is_default": false,
      "requires_2d_drawing": false
    },
    {
      "name": "This part requires tolerances tighter than ±.005″ (±0.13mm)",
      "applicable_group": "metal",
      "is_default": false,
      "requires_2d_drawing": true
    },
    {
      "name": "±.010″ (±0.25mm)",
      "applicable_group": "plastic",
      "is_default": true,
      "requires_2d_drawing": false
    },
    {
      "name": "±.020″ (±0.5mm)",
      "applicable_group": "plastic",
      "is_default": false,
      "requires_2d_drawing": false
    },
    {
      "name": "This part requires tolerances tighter than ±.010″ (±0.25mm)",
      "applicable_group": "plastic",
      "is_default": false,
      "requires_2d_drawing": true
    }
  ],
  "roughnesses": [
    {
      "name": "125uin/3.2um Ra",
      "is_default": true,
      "requires_2d_drawing": false
    },
    {
      "name": "63uin/1.6um Ra",
      "is_default": false,
      "requires_2d_drawing": false
    },
    {
      "name": "32uin/0.8um Ra",
      "is_default": false,
      "requires_2d_drawing": false
    },
    {
      "name": "16uin/0.4um Ra",
      "is_default": false,
      "requires_2d_drawing": true
    }
  ],
  "inspections": [
    {
      "name": "Standard Inspection",
      "code": "STANDARD",
      "is_default": true
    },
    {
      "name": "Formal Inspection with Dimensional Report",
      "code": "FORMAL_DIMENSIONAL",
      "is_default": false
    },
    {
      "name": "CMM Inspection with Dimensional Report",
      "code": "CMM_DIMENSIONAL",
      "is_default": false
    },
    {
      "name": "First Article Inspection Report (FAIR AS9102)",
      "code": "FAIR_AS9102",
      "is_default": false
    },
    {
      "name": "Source Inspection",
      "code": "SOURCE_INSPECTION",
      "is_default": false
    },
    {
      "name": "Build and Hold First Article Inspection",
      "code": "BUILD_AND_HOLD_FAI",
      "is_default": false
    },
    {
      "name": "Custom Inspection",
      "code": "CUSTOM",
      "is_default": false
    }
  ],
  "certifications": [
    {
      "name": "ITAR/EAR Registration",
      "code": "ITAR_EAR"
    },
    {
      "name": "Cybersecurity Maturity Model Certification (CMMC)",
      "code": "CMMC"
    },
    {
      "name": "AS9100 Certified",
      "code": "AS9100"
    },
    {
      "name": "ISO 9001 Certified",
      "code": "ISO_9001"
    },
    {
      "name": "Hardware Certification",
      "code": "HARDWARE_CERT"
    },
    {
      "name": "Certificate of Conformance",
      "code": "C_OF_C"
    },
    {
      "name": "Material Traceability",
      "code": "MATERIAL_TRACEABILITY"
    },
    {
      "name": "JCP/eJCP Certified",
      "code": "JCP_CERTIFIED"
    },
    {
      "name": "Material Certification",
      "code": "MATERIAL_CERT"
    }
  ],
  "markings": [
    {
      "name": "Silkscreen",
      "requires_2d_drawing": true
    },
    {
      "name": "Ink Stamp",
      "requires_2d_drawing": true
    },
    {
      "name": "Bag and Tag",
      "requires_2d_drawing": true
    },
    {
      "name": "Engraving",
      "requires_2d_drawing": true
    },
    {
      "name": "Laser Mark",
      "requires_2d_drawing": false
    }
  ],
  "delivery_tiers": [
    {
      "name": "Economy",
      "code": "economy",
      "is_default": false
    },
    {
      "name": "Standard",
      "code": "standard",
      "is_default": false
    },
    {
      "name": "Fastest / Expedited",
      "code": "fastest",
      "is_default": false
    }
  ]
};

export function useParamCatalog() {
  const loading = ref(false);
  const catalogCache = ref<Record<number, CncParamsCatalog>>({});

  async function loadCatalog(siteType: number) {
    if (catalogCache.value[siteType]) return catalogCache.value[siteType];
    loading.value = true;
    try {
      if (typeof CncPartConfigAPI.getParamsCatalog !== 'function') {
        return null;
      }
      const res = await CncPartConfigAPI.getParamsCatalog(siteType);
      if (res.data && res.data.data) {
        catalogCache.value[siteType] = res.data.data;
        return res.data.data;
      }
    } catch (error) {
      console.warn("加载后端参数字典失败，降级使用本地内置规则库:", error);
    } finally {
      loading.value = false;
    }
    return null;
  }

  return {
    loading,
    catalogCache,
    loadCatalog,
    JLC_DEFAULT_CATALOG,
    XOM_DEFAULT_CATALOG,
  };
}
