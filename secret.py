import streamlit as st
import pandas as pd
import pdfplumber
import os
import io
import re

def extract_all_data(pdf_path):
    """
    Extracts data from all pages of a PDF, mirroring the logic from Pro_CC_ID_pdf_to_excel.py
    for Result and Data Alarm.
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
                if not parts or parts[0] in ["R2", "R3"]:
                    continue

                result = ""
                unit = ""
                data_alarm = "N"
                
                has_plus = line.startswith('+')
                
                # Logic from Pro_CC_ID_pdf_to_excel.py
                if parts[0] == "ISE" or (has_plus and len(parts) > 1 and parts[1] == "ISE"):
                    if has_plus: # "+ ISE K 4.5"
                        if len(parts) >= 4:
                            result = parts[3]
                            data_alarm = "Y" if len(parts) > 4 else "N"
                    else: # "ISE K 4.5"
                        if len(parts) >= 3:
                            result = parts[2]
                            data_alarm = "Y" if len(parts) > 3 else "N"
                elif has_plus: # "+ BILD2-D 0.627"
                    if len(parts) >= 3:
                        result = parts[2]
                        data_alarm = "Y" if len(parts) > 3 else "N"
                else: # "BILD2-D 0.627"
                    if len(parts) >= 2:
                        # Check if the second part is a number, not another word
                        try:
                            float(parts[1].replace(',', '.'))
                            result = parts[1]
                            data_alarm = "Y" if len(parts) > 2 else "N"
                        except (ValueError, IndexError):
                            pass # Not a valid result line

                if result:
                    # Next line might contain the Unit
                    if (line_num) < len(lines):
                        next_line = lines[line_num].strip()
                        next_parts = next_line.split()
                        # A simple check to see if the next line is a unit or a new test
                        if next_parts and not re.match(r'^[A-Z][A-Z0-9-]*', next_parts[0]) and next_parts[0] not in ["ISE", "+", "R2", "R3"]:
                            unit = next_parts[0]

                    # If Unit is blank, Data Alarm should also be blank
                    final_data_alarm = data_alarm if unit else ""

                    all_extracted_data.append({
                        "페이지": page_num,
                        "줄": line_num,
                        "Result": result,
                        "Unit": unit,
                        "Data Alarm": final_data_alarm,
                    })
    return all_extracted_data

def run(pdf_path, original_filename):
    """
    Main function called from app.py.
    Extracts data, creates an Excel file, and provides a download link.
    """
    try:
        if not original_filename:
            st.error("Original PDF filename was not provided.")
            return

        extracted_data = extract_all_data(pdf_path)
        
        if not extracted_data:
            st.warning("No data could be extracted from the PDF. (PDF에서 데이터를 추출할 수 없습니다.)")
            return

        df = pd.DataFrame(extracted_data)

        # Convert 'Result' to numeric where possible, mimicking Pro_CC_ID logic
        def to_numeric_if_possible(value):
            try:
                return float(str(value).replace(',', '.'))
            except (ValueError, TypeError):
                return value
        
        df['Result'] = df['Result'].apply(to_numeric_if_possible)

        # Add and order columns as requested
        df["수정할 Result"] = ""
        df = df[["페이지", "줄", "Result", "Unit", "Data Alarm", "수정할 Result"]]

        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
            
            # Get the worksheet object
            worksheet = writer.sheets['Sheet1']

            # Set column widths (approximate conversion from pixels)
            # 96 pixels for column E, 111 pixels for column F
            worksheet.column_dimensions['E'].width = 13.71 # 96 pixels
            worksheet.column_dimensions['F'].width = 15.86 # 111 pixels
        
        data = output.getvalue()

        # Create download filename as requested
        base_name = os.path.splitext(original_filename)[0]
        download_filename = f"츄릅 엑셀_{base_name}.xlsx"

        st.success("✅ Excel file is ready for download! (Excel 파일이 준비되었습니다!)")
        st.download_button(
            label="📥 Download Extracted Excel (추출된 Excel 다운로드)",
            data=data,
            file_name=download_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"An error occurred in secret.py: {e}")
        import traceback
        st.code(traceback.format_exc())
