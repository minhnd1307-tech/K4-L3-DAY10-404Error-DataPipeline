import sys
from pathlib import Path

# Thêm thư mục src vào sys.path để pytest luôn tìm thấy các package nội bộ (core, retrieval, ingestion, ...)
src_path = Path(__file__).resolve().parents[1] / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
