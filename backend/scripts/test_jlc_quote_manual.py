"""Manual verification script for JLC CNC auto-quoting.

Usage:
  backend\\.venv\\Scripts\\python.exe backend/scripts/test_jlc_quote_manual.py [step_file_path]
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Fix Windows console UTF-8 output encoding for symbols like mm³, mm²
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.modules.cnc.quote.jlc_quote_service import execute_jlc_quote


async def main():
    # Default to sample test drawing if not provided
    if len(sys.argv) > 1:
        step_path = Path(sys.argv[1]).resolve()
    else:
        step_path = backend_dir / "static" / "upload" / "L018-5-M12.step"

    if not step_path.exists():
        print(f"[-] 错误：图纸文件不存在: {step_path}")
        sys.exit(1)

    print(f"[*] 开始手动测试嘉立创自动报价...")
    print(f"[*] 图纸路径: {step_path}")
    print(f"[*] 参数: 数量=1, 材料=铝合金-6061, 表面处理=喷砂+普通阳极氧化 - 本色 - 哑光, 交期档位=标准")
    print("[*] 正在拉起无头浏览器执行自动报价（通常耗时约 10~15 秒），请稍候...\n")

    try:
        result = await execute_jlc_quote(
            step_file_path=step_path,
            quantity=1,
            material="铝合金-6061",
            surface_finish="喷砂+普通阳极氧化 - 本色 - 哑光",
            tolerance="GB/T 1804-2000 m级",
            lead_time_pref="标准",
        )
        print("[+] 报价流程执行成功！返回数据如下：")
        output_json = json.dumps(result, ensure_ascii=False, indent=2)
        try:
            print(output_json)
        except UnicodeEncodeError:
            print(output_json.encode("utf-8", errors="replace").decode("utf-8"))
        print(f"\n[+] 凭证截图已保存至: {backend_dir / result.get('evidence_screenshot', '')}")
    except Exception as exc:
        print(f"[-] 执行失败: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
