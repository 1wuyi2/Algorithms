import pandas as pd
import re

def clean_course_data(df: pd.DataFrame) -> pd.DataFrame:
    """清洗课程数据：解析星期/节次，推断校区，计算周学时等"""
    df = df.copy()
    
    # 解析星期
    def parse_weekday(val):
        if pd.isna(val):
            return None
        match = re.search(r'\d+', str(val))
        return int(match.group()) if match else None
    df["weekday"] = df["weekday_raw"].apply(parse_weekday)
    
    # 解析节次
    def parse_sections(val):
        if pd.isna(val):
            return None, None
        parts = str(val).split('/')
        if len(parts) == 2:
            try:
                return int(parts[0]), int(parts[1])
            except:
                return None, None
        elif str(val).isdigit():
            s = int(val)
            return s, s
        return None, None
    df[["start_section", "end_section"]] = df["sections_raw"].apply(
        lambda x: pd.Series(parse_sections(x))
    )
    
    # 根据节次推算周学时
    df["weekly_hours"] = df.apply(
        lambda r: (r["end_section"] - r["start_section"] + 1) if pd.notnull(r["start_section"]) else 3,
        axis=1
    )
    
    # 推断校区
    def get_campus(classroom):
        if pd.isna(classroom):
            return None
        if "八里台" in classroom:
            return "八里台"
        elif "津南" in classroom:
            return "津南"
        elif "泰达" in classroom:
            return "泰达"
        return None
    df["campus"] = df["classroom"].apply(get_campus)
    
    # 填充空值
    df["teacher_name"] = df["teacher_name"].fillna("").astype(str)
    df["weeks"] = df["weeks"].fillna("2-18")
    
    # 删除临时列
    df.drop(columns=["weekday_raw", "sections_raw"], inplace=True, errors="ignore")
    return df