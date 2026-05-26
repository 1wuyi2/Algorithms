import pdfplumber
import pandas as pd
import re

def parse_catalog_file(file_path: str, semester: str) -> pd.DataFrame:
    ext = file_path.split('.')[-1].lower()
    if ext == 'pdf':
        return _parse_pdf_fixed(file_path, semester)
    elif ext in ['xlsx', 'xls']:
        df = pd.read_excel(file_path)
        return _clean_dataframe(df, semester)
    elif ext == 'csv':
        df = pd.read_csv(file_path)
        return _clean_dataframe(df, semester)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

def _parse_pdf_fixed(pdf_path: str, semester: str) -> pd.DataFrame:
    """
    固定列顺序解析（南开选课手册表格结构固定）
    列索引: 0选课序号,1课程名称,2模块,3选课名额,4跨专业名额,
           5教师,6星期,7节次,8起止周次,9教室,10备注
    """
    all_rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue
                if not any(row and isinstance(row[0], str) and "选课序号" in row[0] for row in table[:2]):
                    continue
                # 确定数据起始行
                start_row = 1
                for i, row in enumerate(table):
                    if row and len(row) > 0 and row[0] and str(row[0]).strip().isdigit():
                        start_row = i
                        break
                for row in table[start_row:]:
                    if not row or len(row) < 11:
                        continue
                    course_code = row[0]
                    if not course_code or str(course_code).strip() == "":
                        continue
                    def get(idx):
                        return row[idx].strip() if idx < len(row) and row[idx] is not None else ""
                    all_rows.append({
                        "course_code": str(course_code).strip(),
                        "course_name": get(1),
                        "module": get(2),
                        "quota": _to_int(get(3)),
                        "cross_major_quota": _to_int(get(4)),
                        "teacher_name": get(5),
                        "weekday_raw": get(6),
                        "sections_raw": get(7),
                        "weeks": get(8),
                        "classroom": get(9),
                        "remark": get(10),
                        "semester": semester
                    })
    return pd.DataFrame(all_rows)

def _to_int(value):
    try:
        if isinstance(value, (int, float)):
            return int(value)
        if not value:
            return 0
        num = re.search(r'\d+', str(value))
        return int(num.group()) if num else 0
    except:
        return 0

def _clean_dataframe(df: pd.DataFrame, semester: str) -> pd.DataFrame:
    df.columns = [c.strip().lower() for c in df.columns]
    rename_map = {
        "选课序号": "course_code",
        "课程名称": "course_name",
        "课程归属模块": "module",
        "选课名额": "quota",
        "跨专业名额": "cross_major_quota",
        "教师": "teacher_name",
        "星期": "weekday_raw",
        "节次": "sections_raw",
        "起止周次": "weeks",
        "教室": "classroom",
        "备注": "remark"
    }
    df.rename(columns=rename_map, inplace=True)
    df["semester"] = semester
    return df