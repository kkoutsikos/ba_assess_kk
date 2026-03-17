from pydantic import BaseModel, Field, model_validator
from typing import List
from datetime import date

class AddressInfo(BaseModel):
    name: str
    street: str
    zip_code: str
    city: str
    vat_id: str

class InvoiceItem(BaseModel):
    pos: int
    description: str
    quantity: float
    unit_price: float
    total: float

    @model_validator(mode='after')
    def validate_line_total(self) -> 'InvoiceItem':
        # Επαλήθευση ότι το γινόμενο ισούται με το σύνολο της γραμμής
        expected = round(self.quantity * self.unit_price, 2)
        if abs(self.total - expected) > 0.01:
            raise ValueError(f"Math error at Pos {self.pos}: {self.quantity} * {self.unit_price} != {self.total}")
        return self

class Invoice(BaseModel):
    invoice_number: str
    date: date
    seller: AddressInfo
    buyer: AddressInfo
    items: List[InvoiceItem]
    net_amount: float
    vat_rate: float = 19.0
    vat_amount: float
    gross_amount: float
    payment_terms: str
    iban: str

    @model_validator(mode='after')
    def validate_invoice_totals(self) -> 'Invoice':
        # 1. Έλεγχος αν το άθροισμα των γραμμών ισούται με το καθαρό ποσό
        calculated_net = sum(item.total for item in self.items)
        if abs(self.net_amount - calculated_net) > 0.01:
            raise ValueError(f"Net amount mismatch: {self.net_amount} != sum of items {calculated_net}")
        
        # 2. Έλεγχος υπολογισμού ΦΠΑ: $VAT = Net \times 0.19$
        expected_vat = round(self.net_amount * (self.vat_rate / 100), 2)
        if abs(self.vat_amount - expected_vat) > 0.01:
            raise ValueError(f"VAT calculation error: expected {expected_vat}")
            
        # 3. Έλεγχος μικτού ποσού: $Gross = Net + VAT$
        expected_gross = round(self.net_amount + self.vat_amount, 2)
        if abs(self.gross_amount - expected_gross) > 0.01:
            raise ValueError(f"Gross amount mismatch: {self.gross_amount} != {self.net_amount} + {self.vat_amount}")
        return self