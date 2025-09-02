import pandas as pd
import re
from langchain_google_genai import GoogleGenerativeAI
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain.prompts import PromptTemplate
from sqlalchemy import create_engine

def query_analyzer(question: str, api_key: str):
    """
    Takes a user's question in natural language, converts it to a SQL query,
    executes it against the survey database, and returns a summarized answer.

    Args:
        question (str): The user's question about the survey data.
        api_key (str): The Google API key for the Gemini model.

    Returns:
        tuple: A tuple containing the final summary (str), the cleaned SQL query (str),
               and the resulting pandas DataFrame. Or (error_message, None, None) on failure.
    """
    # -----------------------------
    # 1️⃣ Setup SQLite connection
    # -----------------------------
    try:
        engine = create_engine("sqlite:///survey_results.db")
        db = SQLDatabase(engine)
    except Exception as e:
        error_msg = f"Error connecting to database: {e}"
        print(error_msg)
        return error_msg, None, None

    # -----------------------------
    # 2️⃣ Initialize Gemini LLM
    # -----------------------------
    try:
        llm = GoogleGenerativeAI(
            google_api_key=api_key,
            model="gemini-2.0-flash" # Using a standard model name
        )
    except Exception as e:
        error_msg = f"Error initializing LLM. Please check your API key. Details: {e}"
        print(error_msg)
        return error_msg, None, None


    # -----------------------------
    # 3️⃣ Custom SQL prompt
    # -----------------------------
    custom_prompt = PromptTemplate(
        input_variables=["table_info", "input"],
        template="""
You are an expert SQLite query generator.

Database schema:
{table_info}

Important rules:
- Use only SELECT queries.
- Table "Sheet1" has: Question_no, Question, Answer.
- Table "Sheet2" has user responses.
   The column headers are the qeustions and the row values are the column's respective responses
  • PRET1 → PRET15 = pre-test answers for questions 1 → 15.
  • POSTT1 → POSTT15 = post-test answers for questions 1 → 15.
  • PRET_SCORE and POSTT_SCORE store total scores.
- To check correctness, compare PRETn or POSTTn against Sheet1.Answer where Question_no = n.
- Always return syntactically valid SQLite queries.
- Do not invent table names or columns.
- Respond only with the SQL query (no text, no markdown).

Question: {input}
SQLQuery:
"""
    )

    sql_chain = SQLDatabaseChain.from_llm(
        llm=llm,
        db=db,
        verbose=True,
        return_sql=True,
        prompt=custom_prompt
    )

    # -----------------------------
    # 4️⃣ Utility to clean SQL
    # -----------------------------
    def clean_sql(sql: str) -> str:
        """
        Clean Gemini's output so only raw SQL is returned.
        """
        sql = re.sub(r"^(Question:|SQLQuery:)\s*", "", sql, flags=re.IGNORECASE).strip()
        sql = sql.replace("```", "").replace("sql", "").strip()
        match = re.search(r"(SELECT\s.+)", sql, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return sql

    # -----------------------------
    # 5️⃣ Generate, Clean, and Execute Query
    # -----------------------------
    print(f"🩺 Doctor's Question: {question}")

    # Step 1: Generate SQL
    try:
        raw_sql_result = sql_chain.invoke({"query": question})
        raw_sql = raw_sql_result["result"] if isinstance(raw_sql_result, dict) else raw_sql_result
        print(f"\n📘 Generated SQL (raw):\n{raw_sql}")
    except Exception as e:
        error_msg = f"Error during SQL generation: {e}"
        print(error_msg)
        return error_msg, None, None

    # Step 2: Clean SQL
    sql_query = clean_sql(raw_sql)
    print(f"\n📘 Cleaned SQL:\n{sql_query}")

    # Step 3: Execute SQL
    try:
        result_df = pd.read_sql_query(sql_query, engine)
        print("\n📊 Retrieved Data:\n", result_df.head())
    except Exception as e:
        error_msg = f"SQL Execution Error: {e}\nAttempted Query: {sql_query}"
        print(f"\n⚠️ {error_msg}")
        return error_msg, sql_query, None

    # Step 4: Summarize results with LLM
    summary_prompt = PromptTemplate(
        input_variables=["question", "data"],
        template="""
You are a medical data assistant.
The doctor asked: {question}
Here are the retrieved results:
{data}

Summarize and explain the trends in natural language. Answer the question subtly.
Keep your answers concise but do not miss important details.
Do not give medical advice, only describe the data.
"""
    )
    try:
        final_answer = llm.invoke(summary_prompt.format(
            question=question,
            data=result_df.to_string()
        ))
        print(f"\n💡 LLM's Answer:\n{final_answer}")
        return final_answer, sql_query, result_df
    except Exception as e:
        error_msg = f"Error during summarization: {e}"
        print(error_msg)
        return error_msg, sql_query, result_df
