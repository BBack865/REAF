import streamlit as st
import pandas as pd
import pdfplumber
import os
import re
import numpy as np
import fitz  # PyMuPDF

def apply_changes_to_pdf(pdf_path, excel_path):
    """
    Modifies the PDF based on the '수정할 Result' column in the Excel file.
    Returns a dictionary with status, message, and path to the modified file.
    Enhanced to preserve original font, size, color, and background.
    Also removes extra words after Result when Data Alarm is Y.
    """
    try:
        excel_df = pd.read_excel(excel_path)
        # Filter for rows that have a value in "수정할 Result"
        mod_df = excel_df[pd.to_numeric(excel_df["수정할 Result"], errors='coerce').notnull()].copy()

        if mod_df.empty:
            return {"status": "warning", "message": "수정할 항목이 엑셀 파일에 없습니다.", "path": None}

        doc = fitz.open(pdf_path)
        
        # Convert result columns to string for matching, handling potential float issues
        mod_df['Result_str'] = mod_df['Result'].apply(lambda x: f"{x:.0f}" if isinstance(x, float) and x.is_integer() else str(x))
        mod_df['수정할 Result_str'] = mod_df['수정할 Result'].apply(lambda x: f"{x:.0f}" if isinstance(x, float) and x.is_integer() else str(x))

        for index, row in mod_df.iterrows():
            page_num = int(row['페이지'])
            line_num = int(row['줄'])  # For more precise error messages
            old_result = row['Result_str']
            new_result = row['수정할 Result_str']

            page = doc.load_page(page_num - 1)  # fitz is 0-indexed

            text_instances = page.search_for(old_result)
            if not text_instances:
                return {"status": "error", "message": f"오류: 페이지 {page_num}, 줄 {line_num} 근처에서 원본 값 '{old_result}'을(를) PDF에서 찾을 수 없습니다.", "path": None}

            rect_to_replace = text_instances[0]
            
            # Extract text properties from the original text
            font_info = None
            text_color = (0, 0, 0)  # Default black
            font_size = 8  # Default size
            font_name = "helv"  # Default font
            original_text_span = None
            
            # Find the specific text and extract its properties
            for block in page.get_text("dict")["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            span_rect = fitz.Rect(span["bbox"])
                            # Check if this span overlaps with our target text
                            if span_rect.intersects(rect_to_replace):
                                if old_result in span["text"]:
                                    font_size = span["size"]
                                    font_name = span["font"]
                                    text_color = span["color"]
                                    font_info = span
                                    original_text_span = span
                                    break
                        if font_info:
                            break
                if font_info:
                    break
            
            # Convert color from integer to RGB tuple if needed
            if isinstance(text_color, int):
                # Convert integer color to RGB
                r = (text_color >> 16) & 255
                g = (text_color >> 8) & 255
                b = text_color & 255
                text_color = (r/255.0, g/255.0, b/255.0)
            elif isinstance(text_color, (list, tuple)) and len(text_color) >= 3:
                # Ensure color values are in 0-1 range
                text_color = tuple(c/255.0 if c > 1 else c for c in text_color[:3])
            
            # Remove extra words with patterns like ">Test", "<Test.", "> Test", "< Test" etc.
            # Look for text spans that contain these patterns on the same line as the Result
            extended_rect = rect_to_replace
            pattern = re.compile(r'[><]\s*\w+[.\s]*')  # Matches ">Test", "<Test.", "> Test", "< Test", etc.
            
            # Search for spans that contain the unwanted patterns on the same line
            for block in page.get_text("dict")["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            span_rect = fitz.Rect(span["bbox"])
                            # Check if this span is on the same line (similar y-coordinates)
                            if (abs(span_rect.y0 - rect_to_replace.y0) < 5 and 
                                abs(span_rect.y1 - rect_to_replace.y1) < 5 and
                                span_rect.x0 >= rect_to_replace.x0):  # To the right of result
                                # Check if this span contains unwanted patterns
                                if pattern.search(span["text"]):
                                    # Extend the rectangle to cover the unwanted text
                                    extended_rect = extended_rect.include_rect(span_rect)
            
            rect_to_replace = extended_rect

            # Use redaction to transparently remove the old text (preserving background)
            page.add_redact_annot(rect_to_replace, fill=None)  # No fill = transparent
            page.apply_redactions()
            
            # Calculate text position for better alignment
            # Use the bottom-left for proper text baseline positioning
            text_point = fitz.Point(rect_to_replace.x0, rect_to_replace.y1 - 2)
            
            # Insert the new text with original formatting
            try:
                # Try to use SegoeUI font from Windows system fonts
                segoeui_path = r"C:\Windows\Fonts\segoeui.ttf"
                if os.path.exists(segoeui_path):
                    page.insert_text(text_point,
                                   new_result,
                                   fontsize=font_size,
                                   fontfile=segoeui_path,
                                   color=text_color)
                else:
                    # If SegoeUI not found, use original font
                    page.insert_text(text_point,
                                   new_result,
                                   fontsize=font_size,
                                   fontname=font_name,
                                   color=text_color)
            except:
                # Fallback to standard formatting if font insertion fails
                page.insert_text(text_point,
                               new_result,
                               fontsize=font_size,
                               fontname="helv",
                               color=(0, 0, 0))

        # Create a path for the temporary modified file
        temp_dir = os.path.dirname(pdf_path)
        output_pdf_path = os.path.join(temp_dir, f"modified_{os.path.basename(pdf_path)}")
        
        doc.save(output_pdf_path, garbage=4, deflate=True, clean=True)
        doc.close()
        
        return {"status": "success", "message": "PDF 파일이 성공적으로 수정되었습니다. 아래 버튼을 눌러 다운로드하세요.", "path": output_pdf_path}

    except Exception as e:
        import traceback
        return {"status": "error", "message": f"PDF 수정 중 심각한 오류 발생: {e}\n{traceback.format_exc()}", "path": None}

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
