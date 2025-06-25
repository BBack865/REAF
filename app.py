import streamlit as st
import importlib
import tempfile
import os
import sys

# ─────────────────────────────────────────────────────────────────────────────
# Add local directory to Python module search path so module files load correctly
# ─────────────────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Simple user credentials (username:password)
USERS = {
    "RDKR": "nakakojo",
}

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "skip_login" not in st.session_state:
    st.session_state.skip_login = False
if "username" not in st.session_state:
    st.session_state.username = None

# ─────────────────────────────────────────────────────────────────────────────
# Login screen
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.logged_in and not st.session_state.skip_login:
    st.title("REAF Beta")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔓 Use without Login\n(로그인 없이 사용)"):
            st.session_state.skip_login = True
    with col2:
        uname = st.text_input("Username (아이디)")
        pwd   = st.text_input("Password (비밀번호)", type="password")
        if st.button("Login (로그인)"):
            if USERS.get(uname) == pwd:
                st.session_state.logged_in = True
                st.session_state.username  = uname
            else:
                st.error("❌ Invalid username or password (아이디 또는 비밀번호 오류)")
    st.stop()

# Display login status in sidebar
if st.session_state.logged_in:
    st.sidebar.success(f"🔓 Logged in: {st.session_state.username} (로그인됨: {st.session_state.username})")
else:
    st.sidebar.info("👤 Using without login (로그인 없이 사용 중)")

# ─────────────────────────────────────────────────────────────────────────────
# Main UI
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("📄 PDF to Excel Converter (PDF → Excel 변환 도구)")

# Usage Tips section
with st.expander("💡 사용 팁 (Usage Tips)", expanded=False):
    st.markdown("""
    **📋 사용 방법:**
    1. **PDF 파일 업로드**: 변환할 PDF 파일을 선택하세요
    2. **장비 선택**: cobas Pro CC 또는 cobas Pro IM 중 선택
    3. **모드 선택**: 
       - **Barcode mode**: Sample ID 기반 변환
       - **Sequence mode**: Sequence Number 기반 변환
    4. **변환 시작**: 버튼을 클릭하여 변환을 시작하세요
    
    **⚠️ 주의사항:**
    - PDF 파일은 cobas Pro 장비에서 생성된 파일이어야 합니다
    - **장비별로 PDF 파일을 분류해서 실행해야 합니다**
    - **파일 크기가 클 경우, 데이터가 누락 될 수 있습니다**
    - 파일 크기가 클 경우 변환에 시간이 소요될 수 있습니다
    - 변환 완료 후 Excel 파일명을 지정할 수 있습니다
    
    **🔧 지원 장비:**
    - **cobas Pro CC**: Barcode/Sequence 모드 모두 지원
    - **cobas Pro IM**: Barcode/Sequence 모드 모두 지원
    
    ---
    
    **📋 How to Use:**
    1. **Upload PDF File**: Select the PDF file to convert
    2. **Select Analyzer**: Choose between cobas Pro CC or cobas Pro IM
    3. **Select Mode**: 
       - **Barcode mode**: Sample ID-based conversion
       - **Sequence mode**: Sequence Number-based conversion
    4. **Start Conversion**: Click the button to start conversion
    
    **⚠️ Important Notes:**
    - PDF files must be generated from cobas Pro analyzers
    - **PDF files must be classified and executed by analyzer type**
    - **Large file sizes may cause data loss**
    - Large files may take longer to convert
    - You can specify the Excel filename after conversion
    
    **🔧 Supported Analyzers:**
    - **cobas Pro CC**: Supports both Barcode/Sequence modes
    - **cobas Pro IM**: Supports both Barcode/Sequence modes
    """)

# PDF uploader
pdf_file = st.file_uploader("Upload PDF File (PDF 파일 업로드)", type=["pdf"])

# Analyzer and mode selection
device = st.selectbox("Select Analyzer (장비 선택)", ["cobas Pro CC (c503, c703)", "cobas Pro IM (e801)"])
mode_options = ["Barcode mode (Barcode 모드)", "Sequence mode (Sequence 모드)"]
mode = st.selectbox("Select Mode (모드 선택)", mode_options)

# Start conversion button
if st.button("🔄 Start Conversion (변환 시작)"):
    if pdf_file is None:
        st.error("Please upload a PDF file. (PDF 파일을 업로드 해주세요.)")
    else:
        # Save uploaded PDF to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_file.getbuffer())
            tmp_path = tmp.name

        # Map to module names (without file extension)
        module_map = {
            ("cobas Pro CC (c503, c703)", "Barcode mode (Barcode 모드)"):  "Pro_CC_ID_pdf_to_excel",
            ("cobas Pro CC (c503, c703)", "Sequence mode (Sequence 모드)"): "Pro_CC_Seq_pdf_to_excel",
            ("cobas Pro IM (e801)", "Barcode mode (Barcode 모드)"):  "Pro_IM_ID_pdf_to_excel",
            ("cobas Pro IM (e801)", "Sequence mode (Sequence 모드)"): "Pro_IM_Seq_pdf_to_excel",
        }
        mod_name = module_map.get((device, mode))
        if not mod_name:
            st.error("Unsupported analyzer/mode combination. (지원하지 않는 장비/모드 조합입니다.)")
            st.stop()

        # Dynamically import and run the selected module
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            st.error(f"Failed to load module: {mod_name} (모듈 불러오기 실패)\n{str(e)}")
            st.stop()

        # Convert PDF to Excel
        with st.spinner("Converting... please wait. (변환 중입니다. 잠시만 기다려주세요...)"):
            try:
                output_path = mod.run(tmp_path)
            except Exception as e:
                st.error(f"Error during PDF conversion: {str(e)} (PDF 변환 중 오류 발생)")
                st.stop()

        # Provide download link for the generated Excel file with filename input
        if output_path and os.path.exists(output_path):
            with open(output_path, "rb") as f:
                data = f.read()
            # PDF 파일명과 동일한 이름으로 기본값 설정 (확장자만 .xlsx로 변경)
            pdf_filename = os.path.basename(pdf_file.name)
            base_name = os.path.splitext(pdf_filename)[0]
            default_name = f"{base_name}.xlsx"
            save_name = st.text_input("Save as (저장 이름)", default_name)
            st.success("✅ Conversion completed! (변환이 완료되었습니다!)")
            st.download_button(
                label="📥 Download Excel (Excel 다운로드)",
                data=data,
                file_name=save_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Failed to generate Excel file. (엑셀 파일을 생성하지 못했습니다.)")

# Secret button for RDKR user
if st.session_state.logged_in and st.session_state.username == "RDKR":
    st.markdown("---")
    st.subheader("비밀의 PDF 츄릅 기능")

    # Part 1: Extract PDF to Excel
    st.markdown("##### 1. PDF에서 Excel 데이터 추출")
    extract_pdf = st.file_uploader("Upload PDF File (츄릅용 Excel로 추출할 PDF 첨부하기)", type=["pdf"], key="extract_pdf")
    
    if st.button("PDF 츄릅용 Excel 추출하기"):
        if extract_pdf:
            with st.spinner("Excel 추출 중..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    tmp_pdf.write(extract_pdf.getbuffer())
                    extract_pdf_path = tmp_pdf.name
                
                try:
                    secret_mod = importlib.import_module("secret")
                    importlib.reload(secret_mod)
                    # The second argument is ignored in secret.py, so pass None
                    secret_mod.run(extract_pdf_path, None) 
                except Exception as e:
                    st.error(f"secret.py 실행 중 오류 발생: {e}")
        else:
            st.error("추출할 PDF 파일을 업로드해야 합니다.")

    st.markdown("---")

    # Part 2: Modify PDF with Excel
    st.markdown("##### 2. Excel 데이터로 PDF 수정 (츄릅)")
    col1, col2 = st.columns(2)
    with col1:
        modify_excel = st.file_uploader("Upload Excel File (츄릅용 Excel 첨부하기, 수정할 값 입력 필수)", type=["xlsx", "xls"], key="modify_excel")
    with col2:
        modify_pdf = st.file_uploader("Upload PDF File (츄릅할 PDF 첨부하기)", type=["pdf"], key="modify_pdf")

    if st.button("PDF 츄릅 하기"):
        if modify_excel and modify_pdf:
            with st.spinner("PDF 츄릅 중..."):
                # Save uploaded files to temp files
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_excel:
                    tmp_excel.write(modify_excel.getbuffer())
                    modify_excel_path = tmp_excel.name
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    tmp_pdf.write(modify_pdf.getbuffer())
                    modify_pdf_path = tmp_pdf.name

                try:
                    secret2_mod = importlib.import_module("secret2")
                    importlib.reload(secret2_mod)
                    secret2_mod.run(modify_pdf_path, modify_excel_path)
                except ModuleNotFoundError:
                    st.error("'secret2.py' 파일을 찾을 수 없습니다. 파일을 생성해주세요.")
                except Exception as e:
                    st.error(f"secret2.py 실행 중 오류 발생: {e}")
        else:
            st.error("수정용 Excel과 PDF 파일을 모두 업로드해야 합니다.")

# Sidebar version info
st.sidebar.markdown("---")
st.sidebar.markdown("Version: 0.0.4 (버전: 0.0.4)")

