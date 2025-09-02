import streamlit as st
from survey_analyzer import query_analyzer

st.set_page_config(page_title="Survey Data Analyzer", layout="wide")

# --- Page Title and Description ---
st.title("🩺 Medical Survey Data Analyzer")
st.markdown("""
Welcome, Doctor! Ask a question in plain English about the survey results,
and I'll provide a summarized answer based on the database.
""")


api_key = "AIzaSyB_IdWI6rPIJVbzojBtmjupIUq3jRfiUuA"


# --- Sample Questions ---
st.sidebar.subheader("Sample Questions")
sample_questions = [
    "Show the average pre-test and post-test scores.",
    "Which 5 participants showed the most improvement from pre-test to post-test?",
    "What is the average score for question 5 in the post-test?",
    "How many participants scored higher on the post-test than the pre-test?",
    "Which questions were answered correctly by most participants in the pre-test?",
]
selected_question = st.sidebar.selectbox(
    "Choose a sample question or write your own below:",
    [""] + sample_questions
)


# --- User Input ---
st.header("Ask Your Question")
if selected_question:
    user_question = st.text_area("Your question:", value=selected_question, height=100)
else:
    user_question = st.text_area("Your question:", placeholder="e.g., Show the average pre-test and post-test scores.", height=100)


# --- Submit Button and Processing ---
if st.button("Analyze Data", type="primary"):
    if not api_key:
        st.error("⚠️ Please enter your Google API Key in the sidebar to proceed.")
    elif not user_question:
        st.warning("Please enter a question to analyze.")
    else:
        with st.spinner("Analyzing data... This may take a moment."):
            try:
                # Call the backend logic
                summary, sql_query, df = query_analyzer(user_question, api_key)

                # --- Display Results ---
                st.subheader("💡 Summary")
                st.markdown(summary)

                with st.expander("Show Details"):
                    st.subheader("🔍 Generated SQL Query")
                    st.code(sql_query, language="sql")

                    if df is not None:
                        st.subheader("📊 Raw Data")
                        st.dataframe(df)
                    else:
                        st.info("No data frame was generated from the query.")

            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")

# --- Instructions ---
st.markdown("""
---
**How to Use:**
1.  Enter your Google API Key in the sidebar.
2.  Type your question about the survey data into the text box.
3.  Click 'Analyze Data' to get a natural language summary, the SQL query used, and the raw data.
""")
