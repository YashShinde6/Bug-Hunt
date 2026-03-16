"""CSV Analyzer — detect data quality issues in CSV files."""
import pandas as pd
from typing import Optional


def analyze_csv(file_path: str) -> list[dict]:
    """Analyze a CSV file for data quality issues."""
    bugs = []

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return [{
            "bug_type": "CSV Parse Error",
            "line_number": 1,
            "explanation": f"Failed to parse CSV: {str(e)}",
            "impact": "Data cannot be processed",
            "severity": "critical",
            "suggested_fix": "Check CSV format, encoding, and delimiter",
            "source": "csv_analyzer",
        }]

    total_rows = len(df)
    total_cols = len(df.columns)

    # 1. Missing values
    missing = df.isnull().sum()
    for col in missing[missing > 0].index:
        count = int(missing[col])
        pct = round(count / total_rows * 100, 1)
        bugs.append({
            "bug_type": "Missing Values",
            "line_number": 0,
            "explanation": f"Column '{col}' has {count} missing values ({pct}% of rows)",
            "impact": f"Data completeness issue — {count} rows affected",
            "severity": "high" if pct > 30 else "medium",
            "suggested_fix": f"Fill missing values with df['{col}'].fillna() or drop rows",
            "source": "csv_analyzer",
        })

    # 2. Duplicate rows
    dupes = df.duplicated().sum()
    if dupes > 0:
        bugs.append({
            "bug_type": "Duplicate Rows",
            "line_number": 0,
            "explanation": f"{dupes} duplicate rows detected out of {total_rows} total rows",
            "impact": "Data integrity issue — duplicates may skew analysis",
            "severity": "medium",
            "suggested_fix": "Remove duplicates with df.drop_duplicates()",
            "source": "csv_analyzer",
        })

    # 3. Type inconsistencies
    for col in df.columns:
        if df[col].dtype == object:
            # Try numeric conversion
            numeric_count = pd.to_numeric(df[col], errors="coerce").notna().sum()
            non_null = df[col].notna().sum()
            if 0 < numeric_count < non_null and numeric_count > non_null * 0.5:
                bugs.append({
                    "bug_type": "Type Mismatch",
                    "line_number": 0,
                    "explanation": f"Column '{col}' has mixed types — {numeric_count}/{non_null} values are numeric",
                    "impact": "Type conversion errors during processing",
                    "severity": "high",
                    "suggested_fix": f"Convert to numeric: pd.to_numeric(df['{col}'], errors='coerce')",
                    "source": "csv_analyzer",
                })

    # 4. Empty columns
    empty_cols = [col for col in df.columns if df[col].isna().all()]
    if empty_cols:
        bugs.append({
            "bug_type": "Empty Columns",
            "line_number": 0,
            "explanation": f"Columns {empty_cols} are completely empty",
            "impact": "Unnecessary columns waste memory",
            "severity": "low",
            "suggested_fix": f"Drop empty columns: df.drop(columns={empty_cols})",
            "source": "csv_analyzer",
        })

    # 5. Outlier detection (numeric columns)
    for col in df.select_dtypes(include=["number"]).columns:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        if iqr > 0:
            outliers = ((df[col] < q1 - 3 * iqr) | (df[col] > q3 + 3 * iqr)).sum()
            if outliers > 0:
                bugs.append({
                    "bug_type": "Data Anomaly",
                    "line_number": 0,
                    "explanation": f"Column '{col}' has {outliers} extreme outliers (>3x IQR)",
                    "impact": "Outliers may distort analysis and ML model performance",
                    "severity": "medium",
                    "suggested_fix": f"Investigate outliers: df[df['{col}'] > {q3 + 3*iqr:.2f}]",
                    "source": "csv_analyzer",
                })

    # Add summary if no issues found
    if not bugs:
        bugs.append({
            "bug_type": "No Issues",
            "line_number": 0,
            "explanation": f"CSV looks clean: {total_rows} rows, {total_cols} columns, no major issues",
            "impact": "None",
            "severity": "info",
            "suggested_fix": "No action needed",
            "source": "csv_analyzer",
        })

    return bugs
