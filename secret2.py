import streamlit as st
import pandas as pd
import pdfplumber
import os
import re
import numpy as np

def extract_data_for_validation(pdf_path):
    """PDF에서 검증을 위한 데이터를 추출합니다."""
    all_extracted_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            page_text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if not page_text:
                continue
            lines = page_text.split('\n')
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if not parts or parts[0] in ["R2", "R3"]:
                    continue

                result = ""
                unit = ""
                
                has_plus = line.startswith('+')
                
                if parts[0] == "ISE" or (has_plus and len(parts) > 1 and parts[1] == "ISE"):
                    if has_plus:
                        if len(parts) >= 4: result = parts[3]
                    else:
                        if len(parts) >= 3: result = parts[2]
                elif has_plus:
                    if len(parts) >= 3: result = parts[2]
                else:
                    if len(parts) >= 2:
                        try:
                            float(parts[1].replace(',', '.'))
                            result = parts[1]
                        except (ValueError, IndexError):
                            pass

                if result:
                    if (line_num) < len(lines):
                        next_line = lines[line_num].strip()
                        next_parts = next_line.split()
                        if next_parts and not re.match(r'^[A-Z][A-Z0-9-]*', next_parts[0]) and next_parts[0] not in ["ISE", "+", "R2", "R3"]:
                            unit = next_parts[0]
                    
                    all_extracted_data.append({
                        "페이지": page_num,
                        "줄": line_num,
                        "Result": result,
                        "Unit": unit,
                    })
    return all_extracted_data

def run(pdf_path, excel_path):
    """
    Excel 파일과 PDF 파일을 검증합니다.
    검증에 성공하면 UI에 확인 버튼을 표시하기 위해 세션 상태 플래그를 설정합니다.
    """
    st.session_state['validation_passed'] = False # 상태 초기화

    try:
        try:
            excel_df = pd.read_excel(excel_path)
            required_cols = ["페이지", "줄", "Result", "Unit", "수정할 Result"]
            if not all(col in excel_df.columns for col in required_cols):
                st.error(f"Excel 파일에 필요한 열({', '.join(required_cols)})이 모두 존재하지 않습니다.")
                return
        except Exception as e:
            st.error(f"Excel 파일을 읽는 중 오류가 발생했습니다: {e}")
            return

        pdf_data = extract_data_for_validation(pdf_path)
        if not pdf_data:
            st.warning("PDF에서 데이터를 추출할 수 없습니다.")
            return
        pdf_df = pd.DataFrame(pdf_data)
        
        pdf_df['Result'] = pd.to_numeric(pdf_df['Result'].str.replace(',', '.'), errors='coerce')
        excel_df['Result'] = pd.to_numeric(excel_df['Result'], errors='coerce')
        
        validation_df = excel_df[excel_df["수정할 Result"].isnull() | (excel_df["수정할 Result"] == "")]
        
        if validation_df.empty:
            st.session_state['validation_passed'] = True
            st.info("검증할 항목이 없습니다. 츄릅을 진행할 수 있습니다.")
            return

        merged_df = pd.merge(
            validation_df,
            pdf_df,
            on=["페이지", "줄"],
            how="left",
            suffixes=('_excel', '_pdf')
        )

        mismatched_rows = []
        for index, row in merged_df.iterrows():
            if pd.isnull(row['Result_pdf']):
                mismatched_rows.append(f"페이지 {row['페이지']}, 줄 {row['줄']}: PDF에서 해당 항목을 찾을 수 없습니다.")
                continue

            excel_val = row['Result_excel']
            pdf_val = row['Result_pdf']
            
            # numpy old version compatibility
            if pd.isnull(excel_val) and pd.isnull(pdf_val):
                result_match = True
            elif pd.isnull(excel_val) or pd.isnull(pdf_val):
                result_match = False
            else:
                result_match = np.isclose(excel_val, pdf_val)

            unit_excel = "" if pd.isnull(row['Unit_excel']) else str(row['Unit_excel'])
            unit_pdf = "" if pd.isnull(row['Unit_pdf']) else str(row['Unit_pdf'])
            unit_match = (unit_excel.strip() == unit_pdf.strip())
            
            if not (result_match and unit_match):
                mismatch_details = f"페이지 {row['페이지']}, 줄 {row['줄']}: "
                if not result_match:
                    mismatch_details += f"Result 불일치 (Excel: {row['Result_excel']}, PDF: {row['Result_pdf']}) "
                if not unit_match:
                    mismatch_details += f"Unit 불일치 (Excel: '{unit_excel}', PDF: '{unit_pdf}')"
                mismatched_rows.append(mismatch_details)

        if mismatched_rows:
            st.error("PDF와 Excel 데이터가 일치하지 않습니다. 아래 항목을 확인해주세요:")
            for error in mismatched_rows:
                st.warning(error)
            st.session_state['validation_passed'] = False
        else:
            st.success("✅ PDF와 Excel 데이터가 일치합니다. 츄릅을 진행할 수 있습니다.")
            st.session_state['validation_passed'] = True

    except Exception as e:
        st.error(f"secret2.py 실행 중 오류 발생: {e}")
        import traceback
        st.code(traceback.format_exc())
        st.session_state['validation_passed'] = False