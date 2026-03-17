import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import ValidationError
from models import Invoice

def run_extraction(raw_text: str, max_attempts: int = 3):
    # Αρχικοποίηση μοντέλου με μηδενικό temperature για σταθερότητα
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
    structured_llm = llm.with_structured_output(Invoice)
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "You are a precise data extraction agent. Convert invoice text to JSON."),
        ("human", "Extract from this text:\n{input}\n\n{feedback}")
    ])
    
    current_feedback = ""
    for i in range(max_attempts):
        try:
            chain = prompt_template | structured_llm
            invoice_data = chain.invoke({"input": raw_text, "feedback": current_feedback})
            print("--- VALIDATION REPORT: PASS ---")
            print(f"Successfully processed Invoice: {invoice_data.invoice_number}")
            return invoice_data
        except Exception as e:
            print(f"Attempt {i+1} failed: {str(e)}")
            current_feedback = f"Your previous JSON was invalid. Error: {str(e)}. Please recalculate the totals and fix the fields."
    
    print("--- VALIDATION REPORT: FAIL ---")
    return None

if __name__ == "__main__":
    # Το κείμενο εισόδου από τις προδιαγραφές [cite: 17-35]
    sample_text = """Rechnung Nr. 2024-0892...""" 
    run_extraction(sample_text)