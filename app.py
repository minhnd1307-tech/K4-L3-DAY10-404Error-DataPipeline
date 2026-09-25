from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import streamlit as st

from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question
from retrieval.agent import build_agent, run_agent_question

# Cấu hình trang
st.set_page_config(
    page_title="RAG Data Observability & Retrieval Dashboard",
    page_icon="🔬",
    layout="wide",
)

st.title("🔬 RAG Data Observability & Semantic Retrieval Dashboard")
st.caption("Day 10 — Data Pipeline, Quality Gate & Retrieval Comparison (VinUni AI Engineer)")

settings = load_settings()

# Sidebar: Lựa chọn chế độ và Collection
st.sidebar.header("⚙️ Cấu hình Hệ thống")
mode = st.sidebar.radio(
    "Chọn chế độ xem:",
    ["🔍 Semantic Retrieval & Silent Failure Demo", "📊 Data Quality & Freshness Monitor", "📈 Metrics Comparison (3 States)"]
)

# ---------------------------------------------------------
# TAB 1: RETRIEVAL & SILENT FAILURE DEMO
# ---------------------------------------------------------
if mode == "🔍 Semantic Retrieval & Silent Failure Demo":
    st.subheader("Interactive Semantic Search Across 3 Data States")
    st.markdown(
        """
        Trang này cho phép bạn kiểm chứng trực tiếp hiện tượng **Silent Failure**:
        - **Baseline:** Tìm kiếm trên dữ liệu chuẩn ban đầu.
        - **Corrupted:** Dữ liệu bị tiêm lỗi (nhiễu ký tự, cắt ngắn tiêu đề, xóa tóm tắt).
        - **Repaired:** Dữ liệu sau khi kích hoạt cơ chế tự phục hồi từ bản gốc Raw.
        """
    )

    col_target = st.selectbox(
        "Chọn Vector Collection để truy vấn:",
        [
            ("papers-baseline (Dữ liệu Sạch)", settings.paths.embeddings_json),
            ("papers-corrupted (Dữ liệu Bị Tiêm Lỗi)", settings.paths.corrupted_embeddings_json),
            ("papers-repaired (Dữ liệu Sau Phục Hồi)", settings.paths.repaired_embeddings_json),
        ],
        format_func=lambda x: x[0],
    )
    selected_name, selected_manifest = col_target

    query = st.text_input(
        "Nhập câu hỏi tìm kiếm ngữ nghĩa:",
        value="What are the recent advances in agentic retrieval-augmented generation?",
    )
    top_k = st.slider("Top K kết quả:", min_value=1, max_value=8, value=3)

    if st.button("🚀 Thực hiện Tìm Kiếm & Hỏi Đáp", use_container_width=True):
        if not selected_manifest.exists():
            st.warning(f"⚠️ Chưa tìm thấy file manifest vector: `{selected_manifest.name}`. Hãy đảm bảo pipeline tương ứng đã được chạy.")
        else:
            with st.spinner("Đang tải ChromaDB index và nhúng câu truy vấn..."):
                try:
                    index = LocalEmbeddingIndex.load(settings, embeddings_path=selected_manifest)
                    results = index.search(query, top_k=top_k)
                    ans_result = answer_question(query, settings, index, top_k=top_k)

                    st.markdown("### 💡 Câu trả lời trích xuất (Heuristic QA):")
                    st.info(f"**Đáp án:** {ans_result.answer}")

                    st.markdown("### 📚 Danh sách tài liệu được truy xuất (Top K):")
                    for i, r in enumerate(results, start=1):
                        with st.expander(f"Top {i}: {r.title} (Cosine Similarity Score: {r.score:.4f})", expanded=(i == 1)):
                            st.write(f"**Paper ID:** `{r.paper_id}`")
                            st.write(f"**Tác giả:** {r.metadata.get('authors_joined', 'N/A')}")
                            st.write(f"**Ngày xuất bản:** {r.metadata.get('published', 'N/A')}")
                            st.write(f"**Chuyên ngành:** {r.metadata.get('categories_joined', 'N/A')}")
                            st.markdown("**Nội dung Embed:**")
                            st.code(r.content, language="markdown")
                except Exception as e:
                    st.error(f"Lỗi khi truy vấn ChromaDB: {e}")

# ---------------------------------------------------------
# TAB 2: DATA OBSERVABILITY & FRESHNESS MONITOR
# ---------------------------------------------------------
elif mode == "📊 Data Quality & Freshness Monitor":
    st.subheader("Data Quality Gate (Great Expectations 1.x) & Freshness SLA")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🛡️ Baseline Quality Gate")
        if settings.paths.baseline_quality_report.exists():
            with open(settings.paths.baseline_quality_report, "r", encoding="utf-8") as f:
                b_quality = json.load(f)
            status = b_quality.get("success", False)
            if status:
                st.success("✅ **Quality Check: PASS (100% Expectations Succeeded)**")
            else:
                st.error("❌ **Quality Check: FAILED**")
            st.json(b_quality)
        else:
            st.info("Chưa có `baseline_quality_report.json`. Hãy chạy `script/run_phase1.py`.")

    with col2:
        st.markdown("#### 🚨 Corrupted Data Quality Gate")
        if settings.paths.corrupted_quality_report.exists():
            with open(settings.paths.corrupted_quality_report, "r", encoding="utf-8") as f:
                c_quality = json.load(f)
            status = c_quality.get("success", False)
            if not status:
                st.error("🚨 **Quality Gate Violated! Bắt được dữ liệu bẩn thành công.**")
            else:
                st.warning("Quality check bất ngờ pass trên dữ liệu bẩn.")
            st.json(c_quality)
        else:
            st.info("Chưa có `corrupted_quality_report.json`. Hãy chạy `script/run_corruption_flow.py`.")

    st.markdown("---")
    st.markdown("#### ⏳ Giám sát độ tươi dữ liệu (Freshness SLA)")
    if settings.paths.freshness_report.exists():
        with open(settings.paths.freshness_report, "r", encoding="utf-8") as f:
            freshness_data = json.load(f)
        st.json(freshness_data)
    else:
        st.info("Chưa có `freshness_report.json`.")

    # Biểu đồ phân bố độ tuổi bài báo nếu có clean_csv
    if settings.paths.clean_csv.exists():
        st.markdown("#### 📊 Phân bố độ tuổi bài báo (`age_days`)")
        df_clean = pd.read_csv(settings.paths.clean_csv)
        if "age_days" in df_clean.columns:
            st.bar_chart(df_clean.set_index("paper_id")["age_days"])

# ---------------------------------------------------------
# TAB 3: METRICS COMPARISON (3 STATES)
# ---------------------------------------------------------
elif mode == "📈 Metrics Comparison (3 States)":
    st.subheader("Bảng Đối Chiếu Định Lượng Hiệu Năng 3 Trạng Thái")
    st.markdown(
        """
        Đối chiếu các chỉ số chất lượng RAG trên 3 trạng thái:
        **Baseline (Sạch) $\\rightarrow$ Corrupted (Bị lỗi) $\\rightarrow$ Repaired (Đã phục hồi)**.
        """
    )

    metrics_rows = []
    for label, path in [
        ("Baseline (Clean)", settings.paths.baseline_metrics),
        ("Corrupted (Dirty)", settings.paths.corrupted_metrics),
        ("Repaired (Self-healed)", settings.paths.repaired_metrics),
    ]:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            metrics_rows.append({
                "Trạng thái": label,
                "Retrieval Hit Rate": data.get("retrieval_hit_rate", 0.0),
                "Mean Token F1": data.get("mean_token_f1", 0.0),
                "LLM Judge Avg Score": data.get("judge_average_score", 0.0),
            })
        else:
            metrics_rows.append({
                "Trạng thái": label,
                "Retrieval Hit Rate": "Chưa có",
                "Mean Token F1": "Chưa có",
                "LLM Judge Avg Score": "Chưa có",
            })

    st.table(pd.DataFrame(metrics_rows))

    if settings.paths.comparison_report.exists():
        st.markdown("### 📄 Nội dung báo cáo Markdown (`corruption_report.md`):")
        with open(settings.paths.comparison_report, "r", encoding="utf-8") as f:
            st.markdown(f.read())
