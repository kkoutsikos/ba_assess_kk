from pydantic import BaseModel, Field, model_validator
from typing import List
from datetime import date
from decimal import Decimal
import math

class AddressInfo(BaseModel):
    name: str = Field(description="The full name of the company")
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
        expected = self.quantity * self.unit_price
        if not math.isclose(self.total, expected, abs_tol=0.01):
            raise ValueError(f"Math Error at pos {self.pos}: {self.quantity} * {self.unit_price} != {self.total}")
        return self

class Invoice(BaseModel):
    invoice_number: str
    date: str = Field(description="Date as written on the invoice")
    seller: AddressInfo
    buyer: AddressInfo
    items: List[InvoiceItem]
    net_amount: float
    vat_rate: float = Field(description="VAT rate as a number (e.g., 19.0)")
    vat_amount: float
    gross_amount: float
    payment_terms: str
    iban: str

    @model_validator(mode='after')
    def validate_invoice_totals(self) -> 'Invoice':
        # 1. Verify line item totals sum to net amount
        calculated_net = sum(item.total for item in self.items)
        if not math.isclose(self.net_amount, calculated_net, abs_tol=0.01):
            raise ValueError(f"Net Amount Mismatch: {self.net_amount} != sum of lines {calculated_net}")
        
        # 2. Verify VAT calculation
        expected_vat = self.net_amount * (self.vat_rate / 100)
        if not math.isclose(self.vat_amount, expected_vat, abs_tol=0.01):
            raise ValueError(f"VAT Calculation Error: Expected {expected_vat} based on rate {self.vat_rate}%")
            
        # 3. Verify gross amount
        expected_gross = self.net_amount + self.vat_amount
        if not math.isclose(self.gross_amount, expected_gross, abs_tol=0.01):
            raise ValueError(f"Gross Amount Mismatch: {self.gross_amount} != {self.net_amount} + {self.vat_amount}")
            
        return self