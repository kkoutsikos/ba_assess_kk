import sys
import os
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, "section-1"))
sys.path.append(os.path.join(BASE_DIR, "section-2"))
sys.path.append(os.path.join(BASE_DIR, "section-3"))

# Section imports
import extract
import agent
import transform as transformer
import database

app = FastAPI(title="Invoice Processing App", version="1.0.0")

# Χρήση βάσης δεδομένων από το Section 2
INMEMORY_DB = database.INVOICES

class ExtractRequest(BaseModel):
    text: str = Field(..., description="Raw text of the invoice to extract")

class QueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question about invoices")

class TransformRequest(BaseModel):
    records: List[Dict[str, Any]] = Field(..., description="Flat CSV-style records from System A")

class QueryResponse(BaseModel):
    answer: str
    tools_called: List[str]

@app.get("/invoices", response_model=List[Dict[str, Any]])
def get_all_invoices():
    """Returns all invoices currently stored in memory."""
    return INMEMORY_DB

@app.post("/invoices/extract")
def extract_invoice_endpoint(request: ExtractRequest):
    # Χρήση groq για να αποφύγουμε τα quota limits της Google
    result = extract.extract_invoice(request.text, provider="groq")
    
    if result is None or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail="Could not extract data. Text is empty or invalid."
        )
    
    # Μετατροπή σε dict
    extracted_dict = result.model_dump()
    
    # --- ΓΕΦΥΡΑ ΓΙΑ ΤΟΝ AGENT
    formatted_for_agent = {
        "id": extracted_dict.get("invoice_number"),
        "customer": extracted_dict.get("seller_name"), 
        "date": extracted_dict.get("invoice_date"),
        "net_total": extracted_dict.get("net_amount"),
        "gross_total": extracted_dict.get("gross_amount"),
        "status": "extracted"
    }
    
    # Προσθήκη στην κοινή βάση δεδομένων
    INMEMORY_DB.append(formatted_for_agent)
    
    return extracted_dict

@app.post("/invoices/transform")
def transform_invoices_endpoint(request: TransformRequest):
    result = transformer.transform(request.records)
    
    # Χειρισμός σφαλμάτων validation
    if result.get("validation_errors"):
        serializable_errors = []
        for error in result["validation_errors"]:
            clean_error = {
                "invoice_number": error.get("invoice_number", "Unknown"),
                "error_message": error.get("error_message", "Validation Failed"),
                "details": str(error.get("details", "")) # Μετατροπή ValueError σε string
            }
            serializable_errors.append(clean_error)

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail=serializable_errors
        )
    
    # Έλεγχος αν υπάρχουν επιτυχείς μετασχηματισμοί
    success_list = result.get("successful_transformations", [])
    if not success_list:
         raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail="No valid invoices found in the provided records."
        )
    
    # --- ΓΕΦΥΡΑ ΓΙΑ ΤΟΝ AGENT ---
    for inv in success_list:
        formatted_inv = {
            "id": inv["invoiceNumber"],
            "customer": inv.get("buyer", {}).get("name", "Unknown"), # Buyer = Customer
            "date": inv["issueDate"],
            "net_total": inv.get("totals", {}).get("netAmount"),
            "gross_total": inv.get("totals", {}).get("grossAmount"),
            "status": "transformed"
        }
        INMEMORY_DB.append(formatted_inv)
        
    return result

@app.post("/invoices/query", response_model=QueryResponse)
def query_invoices_endpoint(request: QueryRequest):
    """
    Accepts a natural language question and uses the actual LangGraph agent to answer it.
    """
    config = {"configurable": {"thread_id": "api_thread"}}
    
    
    final_state = agent.app.invoke({"messages": [("user", request.question)]}, config)
    
    
    last_message = final_state['messages'][-1].content
    
    # Δυναμικός εντοπισμός των εργαλείων που αποφάσισε να καλέσει το μοντέλο
    tools_called = []
    for msg in final_state['messages']:
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool in msg.tool_calls:
                tools_called.append(tool['name'])
                
    return QueryResponse(answer=last_message, tools_called=list(set(tools_called)))