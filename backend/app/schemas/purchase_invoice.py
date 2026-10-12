from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.purchase_invoice import EXPENSE_TYPES, ISR_RETENTION_TYPES, PAYMENT_TYPES


class PurchaseInvoiceBase(BaseModel):
    supplier_id: int
    project_id: int | None = None
    ncf: str = Field(min_length=11, max_length=19)
    ncf_modified: str | None = Field(default=None, max_length=19)
    invoice_date: date
    payment_date: date | None = None
    expense_type: str = "09"
    payment_type: str = "04"
    services_amount: Decimal = Field(default=Decimal("0"), ge=0)
    goods_amount: Decimal = Field(default=Decimal("0"), ge=0)
    itbis_invoiced: Decimal = Field(default=Decimal("0"), ge=0)
    itbis_withheld: Decimal = Field(default=Decimal("0"), ge=0)
    isr_withheld: Decimal = Field(default=Decimal("0"), ge=0)
    isr_retention_type: str | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("expense_type")
    @classmethod
    def _check_expense_type(cls, v: str) -> str:
        if v not in EXPENSE_TYPES:
            raise ValueError("Tipo de gasto inválido, debe ser 01-11")
        return v

    @field_validator("payment_type")
    @classmethod
    def _check_payment_type(cls, v: str) -> str:
        if v not in PAYMENT_TYPES:
            raise ValueError("Forma de pago inválida, debe ser 01-07")
        return v

    @field_validator("isr_retention_type")
    @classmethod
    def _check_isr_retention_type(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        if v not in ISR_RETENTION_TYPES:
            raise ValueError("Tipo de retención de ISR inválido, debe ser 01-09")
        return v

    @field_validator("ncf", "ncf_modified")
    @classmethod
    def _normalize_ncf(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else v


class _PurchaseInvoiceInput(PurchaseInvoiceBase):
    """Reglas del instructivo del 606 para lo que se captura. Solo en la entrada: las facturas
    ya guardadas (sin tipo de retención) deben poder listarse igual."""

    @model_validator(mode="after")
    def _check_retention_rules(self):
        if self.isr_withheld > 0 and not self.isr_retention_type:
            raise ValueError("Indica el tipo de retención de ISR (01-09): la DGII lo exige cuando hay retención de renta")
        if (self.isr_withheld > 0 or self.itbis_withheld > 0) and self.payment_date is None:
            raise ValueError("Indica la fecha de pago: la DGII la exige cuando hay ITBIS o renta retenidos")
        if self.isr_withheld == 0:
            self.isr_retention_type = None
        return self


class PurchaseInvoiceCreate(_PurchaseInvoiceInput):
    pass


class PurchaseInvoiceUpdate(_PurchaseInvoiceInput):
    pass


class PurchaseInvoiceOut(PurchaseInvoiceBase):
    id: int
    supplier_name: str | None = None
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
