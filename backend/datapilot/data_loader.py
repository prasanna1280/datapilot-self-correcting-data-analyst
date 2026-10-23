"""Load an uploaded CSV / Excel file into the session sandbox and describe it for the Planner."""

from __future__ import annotations

import io
import shutil
from pathlib import Path

import pandas as pd

ALL_SHEETS = "__all__"
DATA_FILE_NAME = "data.csv"
STYLE_FILE = Path(__file__).with_name("assets") / "datapilot.mplstyle"


def list_sheets(raw: bytes) -> list[str]:
    return pd.ExcelFile(io.BytesIO(raw)).sheet_names


def read_upload(file_name: str, raw: bytes, sheet: str | None = None) -> pd.DataFrame:
    """Read CSV or Excel bytes. For Excel, `sheet=ALL_SHEETS` stacks every sheet
    (adding a `sheet` column) - handy when data is split per month/quarter."""
    suffix = Path(file_name).suffix.lower()
    if suffix in (".xlsx", ".xlsm", ".xls"):
        book = pd.read_excel(io.BytesIO(raw), sheet_name=None)
        if sheet in (None, ALL_SHEETS):
            if len(book) == 1:
                return next(iter(book.values()))
            frames = [df.assign(sheet=name) for name, df in book.items() if not df.empty]
            return pd.concat(frames, ignore_index=True)
        if sheet not in book:
            raise ValueError(f"Sheet '{sheet}' not found. Available: {', '.join(book)}")
        return book[sheet]
    if suffix in (".csv", ".txt"):
        return pd.read_csv(io.BytesIO(raw))
    raise ValueError(f"Unsupported file type '{suffix}'. Upload a .csv or .xlsx file.")


def stage_dataset(df: pd.DataFrame, work_dir: Path) -> Path:
    """Write the dataset as data.csv (plus the house chart style) inside the sandbox folder."""
    work_dir.mkdir(parents=True, exist_ok=True)
    path = work_dir / DATA_FILE_NAME
    df.to_csv(path, index=False)
    shutil.copyfile(STYLE_FILE, work_dir / STYLE_FILE.name)
    return path


def _as_dates(s: pd.Series) -> pd.Series | None:
    """Return the column parsed as dates if (nearly) all values are dates, else None."""
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    sample = s.dropna().astype(str).head(500)
    if sample.empty or not sample.str.match(r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}").all():
        return None
    parsed = pd.to_datetime(s, errors="coerce")
    return parsed if parsed.notna().mean() > 0.95 else None


def profile(df: pd.DataFrame, max_categories: int = 8) -> str:
    """Compact, token-cheap description of the data for the Planner/Coder."""
    lines = [f"Rows: {len(df):,} | Columns: {len(df.columns)}", "Columns (dtype -> examples):"]
    for col in df.columns:
        s = df[col]
        nunique = s.nunique(dropna=True)
        is_text = pd.api.types.is_string_dtype(s) or s.dtype == object
        dates = _as_dates(s) if is_text or pd.api.types.is_datetime64_any_dtype(s) else None
        if dates is not None:
            months = dates.dt.strftime("%Y-%m").dropna().unique()
            months = sorted(months)
            shown = ", ".join(months) if len(months) <= 24 else f"{months[0]} ... {months[-1]}"
            detail = (f"DATE from {dates.min():%Y-%m-%d} to {dates.max():%Y-%m-%d}; "
                      f"{len(months)} months present (YYYY-MM): {shown}")
        elif is_text and nunique <= max_categories:
            examples = ", ".join(map(str, s.dropna().unique()[:max_categories]))
            detail = f"{nunique} values: {examples}"
        elif pd.api.types.is_numeric_dtype(s):
            detail = f"min {s.min()}, max {s.max()}"
        else:
            detail = f"{nunique} unique, e.g. {', '.join(map(str, s.dropna().unique()[:3]))}"
        nulls = int(s.isna().sum())
        lines.append(f"- {col} ({s.dtype}){' [' + str(nulls) + ' nulls]' if nulls else ''} -> {detail}")
    lines.append("First 3 rows (CSV):")
    lines.append(df.head(3).to_csv(index=False).strip())
    return "\n".join(lines)
