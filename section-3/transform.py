from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, ValidationError
import re

# 1. Define the System B Target Schema with Pydantic

class Address(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    postalCode: Optional[str] = None
    countryCode: Optional[str] = None

class Party(BaseModel):
    name: str
    address: Address
    vatId: Optional[str] = None

    @field_validator('vatId')
    @classmethod
    def validate_vat_id(cls, v: str) -> str:
        if v and not re.match(r'^[A-Z]{2}\d+$', v):
            raise ValueError("VAT ID must consist of a 2-letter country code followed by digits.")
        return v

class LineItem(BaseModel):
    description: str
    quantity: int = Field(gt=0, description="Quantity must be strictly greater than 0")
    unitPrice: float = Field(ge=0.0, description="Price cannot be negative")
    vatRate: float = Field(ge=0.0, le=100.0)
    lineTotal: float

class Totals(BaseModel):
    netAmount: float
    vatAmount: float
    grossAmount: float

class PaymentTerms(BaseModel):
    dueDays: int = Field(gt=0)
    dueDate: str

class PaymentMeans(BaseModel):
    iban: str

    @field_validator('iban')
    @classmethod
    def validate_iban(cls, v: str) -> str:
        # ΙΒΑΝ: 2 letters, 2 digits, and up to 30 alphanumeric characters
        if not re.match(r'^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$', v):
            raise ValueError("Invalid IBAN format provided.")
        return v

class SystemBInvoice(BaseModel):
    invoiceNumber: str
    issueDate: str
    seller: Party
    buyer: Party
    lineItems: List[LineItem]
    totals: Totals
    paymentTerms: PaymentTerms
    paymentMeans: PaymentMeans


# Transformation Logic

def transform(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Transforms flat records from System A into nested System B JSON.
    Groups by invoice number and validates output via Pydantic.
    """
    
    # Group flat rows by invoice number
    grouped_invoices = {}
    for record in records:
        inv_num = record.get("invoice_number")
        if not inv_num:
            continue
        if inv_num not in grouped_invoices:
            grouped_invoices[inv_num] = []
        grouped_invoices[inv_num].append(record)

    results = {
        "successful_transformations": [],
        "validation_errors": []
    }

    # Process each grouped invoice
    for inv_num, items in grouped_invoices.items():
        try:
            # Header details are taken from the first row of the group
            first_row = items[0]
            
            # Date formatting (DD.MM.YYYY to ISO 8601)
            raw_date = first_row.get("invoice_date", "")
            issue_date_obj = datetime.strptime(raw_date, "%d.%m.%Y")
            issue_date_iso = issue_date_obj.date().isoformat()
            
            due_days = int(first_row.get("payment_days", 0))
            due_date_obj = issue_date_obj + timedelta(days=due_days)
            due_date_iso = due_date_obj.date().isoformat()

            line_items = []
            net_total = 0.0
            vat_total = 0.0

            # Process all line items for this invoice
            for item in items:
                qty = int(item.get("item_quantity", 0))
                price = float(item.get("item_unit_price", 0.0))
                vat_rate = float(item.get("item_vat_rate", 0.0))
                
                line_total = qty * price
                line_vat = line_total * (vat_rate / 100)
                
                net_total += line_total
                vat_total += line_vat
                
                line_items.append({
                    "description": item.get("item_description", ""),
                    "quantity": qty,
                    "unitPrice": price,
                    "vatRate": vat_rate,
                    "lineTotal": round(line_total, 2)
                })

            gross_total = net_total + vat_total

            # Construct the nested dictionary
            raw_payload = {
                "invoiceNumber": inv_num,
                "issueDate": issue_date_iso,
                "seller": {
                    "name": first_row.get("seller_name", ""),
                    "address": {
                        "street": first_row.get("seller_street", ""),
                        "city": first_row.get("seller_city", ""),
                        "postalCode": first_row.get("seller_zip", ""),
                        "countryCode": first_row.get("seller_country", "")
                    },
                    "vatId": first_row.get("seller_vat_id", "")
                },
                "buyer": {
                    "name": first_row.get("buyer_name", ""),
                    "address": {
                        "city": first_row.get("buyer_city", "")
                    },
                    "vatId": first_row.get("buyer_vat_id", "")
                },
                "lineItems": line_items,
                "totals": {
                    "netAmount": round(net_total, 2),
                    "vatAmount": round(vat_total, 2),
                    "grossAmount": round(gross_total, 2)
                },
                "paymentTerms": {
                    "dueDays": due_days,
                    "dueDate": due_date_iso
                },
                "paymentMeans": {
                    "iban": first_row.get("iban", "")
                }
            }

            # Enforce validation by unpacking the payload into the Pydantic model
            validated_invoice = SystemBInvoice(**raw_payload)
            results["successful_transformations"].append(validated_invoice.model_dump())

        except ValidationError as e:
            # Capture strictly formatted validation errors
            results["validation_errors"].append({
                "invoice_number": inv_num,
                "error_message": "Pydantic Schema Validation Failed",
                "details": e.errors()
            })
        except Exception as e:
            # Capture date parsing errors or missing key errors
            results["validation_errors"].append({
                "invoice_number": inv_num,
                "error_message": "Data Processing Error",
                "details": str(e)
            })

    return results

if __name__ == "__main__":
    import json
    import os
    
    # 3. Test Data provided by System A
    system_a_records = [
        { 
            "invoice_number": "2024-0892", "invoice_date": "15.03.2024",
            "seller_name": "TechSolutions GmbH", "seller_street": "Musterstrasse 42",
            "seller_city": "Berlin", "seller_zip": "10115", "seller_country": "DE",
            "seller_vat_id": "DE123456789",
            "buyer_name": "Digital Services AG", "buyer_city": "Munchen",
            "buyer_vat_id": "DE987654321",
            "item_description": "Cloud Hosting Premium (Jan-Mar 2024)",
            "item_quantity": "3", "item_unit_price": "450.00",
            "item_vat_rate": "19", "payment_days": "30",
            "iban": "DE89370400440532013000" 
        },
        { 
            "invoice_number": "2024-0893", "invoice_date": "16.03.2024",
            "seller_name": "TechSolutions GmbH", "seller_street": "Musterstrasse 42",
            "seller_city": "Berlin", "seller_zip": "10115", "seller_country": "DE",
            "seller_vat_id": "DE123456789",
            "buyer_name": "Digital Services AG", "buyer_city": "Munchen",
            "buyer_vat_id": "DE987654321",
            "item_description": "Excess Bandwidth Usage",
            "item_quantity": "1", "item_unit_price": "120.00",
            "item_vat_rate": "19", "payment_days": "30",
            "iban": "DE89370400440532013000" 
        }
    ]

    print("\nExecuting Middleware Transformation...")
    output = transform(system_a_records)
    print(json.dumps(output, indent=2))
   
    
    
    os.makedirs("section-3", exist_ok=True)
    
    output_filepath = "section-3/transformed_payload.json"
    with open(output_filepath, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=2)
        
    print(f"\n[SUCCESS] Transformed payload securely saved to: {output_filepath}")