from pydantic import BaseModel

class ProductCreate(BaseModel):
    product_name: str
    printer_type: str
    model_name: str