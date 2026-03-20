import os
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
from models import Invoice

load_dotenv()

def save_to_json(invoice_data: Invoice, base_path: str = "section-1"):
    # Δημιουργία φακέλου εξόδου για τα εξαχθέντα δεδομένα
    output_dir = Path(base_path) / "extracted_data"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Ονοματοδοσία βάσει του αριθμού τιμολογίου για αποφυγή επικαλύψεων
    file_name = f"invoice_{invoice_data.invoice_number}.json"
    file_path = output_dir / file_name
    
    # Εγγραφή του αντικειμένου σε μορφή JSON string
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(invoice_data.model_dump_json(indent=2))
    
    print(f"SUCCESS: JSON output saved to {file_path}")


def print_validation_report(invoice: Invoice = None, error: str = None):
    print("\n" + "="*50)
    print("      EXTRACTION VALIDATION REPORT")
    print("="*50)
    if invoice:
        print(f"STATUS:       PASS")
        print(f"INVOICE NO:   {invoice.invoice_number}")
        print(f"SELLER:       {invoice.seller.name}")
        print(f"NET AMOUNT:   {invoice.net_amount:.2f} EUR")
        print(f"GROSS AMOUNT: {invoice.gross_amount:.2f} EUR")
        print(f"ITEMS COUNT:  {len(invoice.items)}")
    else:
        print(f"STATUS:       FAIL")
        print(f"ERROR:        {error}")
    print("="*50 + "\n")

def extract_invoice(text: str, max_retries: int = 3, provider: str = "gemini"):
    # Επιλογή του κατάλληλου LLM βάσει του provider
    if provider == "groq":
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    elif provider == "ollama":
        llm = ChatOllama(model="llama3.1", temperature=0)
    elif provider == "gemini":
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0)
    else:
        raise ValueError(f"Μη υποστηριζόμενος provider: {provider}. Επίλεξε 'ollama', 'groq', ή 'gemini'.")

    structured_llm = llm.with_structured_output(Invoice)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a professional auditor. Extract invoice data into the exact JSON schema provided. Pay close attention to numerical values and mathematical accuracy."),
        ("human", "Text: {text}\n\nFeedback from previous attempt (fix these errors if any): {feedback}")
    ])
    
    feedback = "None"
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries}: Extracting and validating data...")
            chain = prompt | structured_llm
            result = chain.invoke({"text": text, "feedback": feedback})
            print_validation_report(invoice=result)
            return result
        except Exception as e:
            # Τροφοδοτούμε το συγκεκριμένο error πίσω στο μοντέλο
            feedback = f"Validation failed: {str(e)}. Please correct the extracted numerical values."
            print(f"  -> Attempt {attempt+1} failed validation. Error details: {str(e)}")
    
    print_validation_report(error="Max retries reached without passing mathematical validation.")
    return None

if __name__ == "__main__":
    
    raw_inputs = [
        """Rechnung Nr. 2024-0892
Datum: 15.03.2024
Von:
TechSolutions GmbH
Musterstrasse 42
10115 Berlin
USt-IdNr.: DE123456789
An:
Digital Services AG
Hauptweg 7
80331 Munchen
USt-IdNr.: DE987654321
Pos. 1: Cloud Hosting Premium (Jan-Mar 2024) - 3 x 450,00 EUR = 1.350,00 EUR
Pos. 2: SSL-Zertifikat Erneuerung - 1 x 89,50 EUR = 89,50 EUR
Pos. 3: Technischer Support (15 Stunden) - 15 x 95,00 EUR = 1.425,00 EUR
Nettobetrag: 2.864,50 EUR
USt. 19%: 544,26 EUR
Bruttobetrag: 3.408,76 EUR
Zahlungsziel: 30 Tage
Bankverbindung: IBAN DE89 3704 0044 0532 0130 00""" 
    ]

    for raw_data in raw_inputs:
        # Τρέχουμε πλέον με το Gemini για να είμαστε καλυμμένοι με την άσκηση
        extracted_invoice = extract_invoice(raw_data, provider="gemini")
        if extracted_invoice:
            save_to_json(extracted_invoice)