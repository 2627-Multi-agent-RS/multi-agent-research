"""
Khởi tạo và kiểm tra cơ sở dữ liệu Checkpoint SQLite cho Multi-Agent Research System (MAS).
Thiết lập chế độ WAL (Write-Ahead Logging) và kiểm tra toàn vẹn dữ liệu cho LangGraph.
"""
import os
import sys
import sqlite3
from pathlib import Path

def init_checkpoint_db(db_path: str = None):
    if db_path is None:
        base_dir = Path(__file__).resolve().parent.parent
        db_path = base_dir / "storage" / "checkpoints.db"
    else:
        db_path = Path(db_path)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Đang kết nối cơ sở dữ liệu SQLite: {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Kích hoạt WAL (Write-Ahead Logging) để đọc/ghi đồng thời không khóa database
    cursor.execute("PRAGMA journal_mode = WAL;")
    journal_mode = cursor.fetchone()[0]
    print(f"-> Journal Mode: {journal_mode}")

    # Tối ưu hóa hiệu năng đồng bộ khi dùng WAL
    cursor.execute("PRAGMA synchronous = NORMAL;")

    # Bật ràng buộc khóa ngoại
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Kiểm tra tính toàn vẹn
    cursor.execute("PRAGMA integrity_check;")
    integrity = cursor.fetchone()[0]
    print(f"-> Integrity Check: {integrity}")

    conn.commit()
    conn.close()
    print("-> Khởi tạo Checkpoint DB thành công!")

if __name__ == "__main__":
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    init_checkpoint_db(path_arg)
