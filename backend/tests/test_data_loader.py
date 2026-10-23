import io

import pandas as pd
import pytest

from backend.datapilot.data_loader import ALL_SHEETS, list_sheets, profile, read_upload, stage_dataset


def _xlsx(sheets: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name, index=False)
    return buf.getvalue()


def test_csv_profile_mentions_columns(sales_df):
    text = profile(sales_df)
    assert len(sales_df) == 12_480
    for col in ["order_date", "region", "category", "product", "units", "unit_price", "discount"]:
        assert f"- {col} (" in text
    assert "South" in text  # low-cardinality values are listed


def test_excel_all_sheets_are_stacked_with_sheet_column():
    raw = _xlsx({"Q1": pd.DataFrame({"a": [1, 2]}), "Q2": pd.DataFrame({"a": [3]})})
    assert list_sheets(raw) == ["Q1", "Q2"]
    df = read_upload("x.xlsx", raw, ALL_SHEETS)
    assert df["a"].tolist() == [1, 2, 3]
    assert df["sheet"].tolist() == ["Q1", "Q1", "Q2"]
    assert read_upload("x.xlsx", raw, "Q2")["a"].tolist() == [3]


def test_unknown_sheet_and_type_raise():
    raw = _xlsx({"S": pd.DataFrame({"a": [1]})})
    with pytest.raises(ValueError):
        read_upload("x.xlsx", raw, "nope")
    with pytest.raises(ValueError):
        read_upload("x.json", b"{}")


def test_stage_dataset_writes_data_csv(tmp_path, sales_df):
    path = stage_dataset(sales_df.head(5), tmp_path / "s")
    assert path.name == "data.csv" and len(pd.read_csv(path)) == 5
