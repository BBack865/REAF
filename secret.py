import pdfplumber
import pandas as pd
import os
import re
import streamlit as st

def extract_all_data(pdf_path):
    """
    Extracts data from all pages of a PDF based on Pro_CC_ID logic.
    """
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
                if not parts:
                    continue
                
                if parts[0] in ["R2", "R3"]:
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
                    if line_num < len(lines):
                        next_line = lines[line_num].strip()
                        next_parts = next_line.split()
                        if next_parts and any(u in next_line for u in ['mg/dL', 'g/dL', 'mmol/L', 'U/L', '%', 'mEq/L']):
                            unit = next_parts[0]
                    
                    all_extracted_data.append({
                        "페이지": page_num,
                        "줄": line_num,
                        "Result": result.replace(',', '.'),
                        "Unit": unit,
                    })

    return all_extracted_data

def run(pdf_path, excel_path_ignored):
    """
    Main function to be called from app.py.
    """
    st.info(f"츄릅을 시작합니다... PDF 파일: {os.path.basename(pdf_path)}")
    
    try:
        data_to_excel = extract_all_data(pdf_path)
        
        if not data_to_excel:
            st.warning("PDF에서 Result 데이터를 찾을 수 없습니다. (Pro_CC_ID 형식인지 확인해주세요)")
            return

        df = pd.DataFrame(data_to_excel)
        df["수정할 Result"] = ""
        df = df[["페이지", "줄", "Result", "Unit", "수정할 Result"]]
        
        output_dir = os.path.dirname(pdf_path)
        pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
        output_excel_path = os.path.join(output_dir, f"SECRET_EXTRACT_{pdf_basename}.xlsx")
        
        df.to_excel(output_excel_path, index=False)
        
        st.success(f"데이터 추출 완료! 아래는 추출된 데이터입니다.")
        st.dataframe(df)
        
        with open(output_excel_path, "rb") as f:
            data = f.read()
        st.download_button(
            label="📥 추출된 Excel 다운로드",
            data=data,
            file_name=os.path.basename(output_excel_path),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"secret.py 실행 중 심각한 오류 발생: {e}")
        import traceback
        st.code(traceback.format_exc())