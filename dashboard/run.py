"""ตัวเปิด dashboard ที่รองรับ Python 3.10.0rc2

Python 3.10.0rc2 (release candidate) มีบั๊กใน typing._no_init_or_replace_init
ที่ทำให้ tornado WebSocketHandler ของ Streamlit พัง
(TypeError: WebSocketHandler.__init__() missing 2 required positional arguments)

ไฟล์นี้ patch บั๊กดังกล่าว *ก่อน* import streamlit แล้วจึงเปิดเซิร์ฟเวอร์

วิธีรัน:
    python dashboard/run.py
(ถ้าใช้ Python เวอร์ชัน stable เช่น 3.11/3.12 จะรัน `streamlit run dashboard/app.py` ได้ตรง ๆ)
"""
import sys
from pathlib import Path


def _patch_typing_rc_bug():
    """แทนที่ _no_init_or_replace_init ที่บั๊กด้วย no-op (ต้องทำก่อน import streamlit)."""
    import typing

    def _safe_init(self, *args, **kwargs):  # noqa: D401 - protocol init = no-op
        pass

    typing._no_init_or_replace_init = _safe_init
    # เผื่อ Protocol บางคลาสถูกสร้างไปแล้ว ให้แก้ __init__ ที่ยังเป็นตัวบั๊ก
    # (ปกติ launcher นี้รันก่อน import streamlit จึงยังไม่มี แต่กันไว้)


def main():
    _patch_typing_rc_bug()

    from streamlit.web import cli as stcli

    app_path = str(Path(__file__).with_name("app.py"))
    sys.argv = ["streamlit", "run", app_path, "--server.headless=true"]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
