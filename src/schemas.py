from typing import List

from pydantic import BaseModel, Field


class PetDetail(BaseModel):
    type: str = Field(default="N/A", description="Species or type of pet (e.g., Dog, Cat, Bird)")
    breed: str = Field(default="N/A", description="Breed or mix of the pet (e.g., Labrador mix, Siamese)")
    name: str = Field(default="N/A", description="Name of the pet if mentioned (e.g., Buster)")
    additional_information: str = Field(default="N/A", description="Any additional information about the pet provided by the applicant (e.g., 'small dog', 'indoor cat')")
    weight: str = Field(default="N/A", description="Declared weight of the pet (e.g., 82 lbs, ~14-15 lbs)")


class Pets(BaseModel):
    all_pets_quantity: int = Field(default=1, description="Number of all the pets declared by the applicant, including multiple pets of the same type")
    all_pets: List[PetDetail] = Field(default_factory=list, description="List of pets declared by the applicant, one entry for each pet. If multiple pets of the same type are declared, they should be listed separately with their own details.")

class MonthlyRent(BaseModel):
    written_form: str = Field(default="N/A", description="Rent amount in words as written on the form (e.g., 'One Thousand Five Hundred Dollars')")
    amount: str = Field(default="N/A", description="Numeric rent amount with currency symbol (e.g., '$1,500.00')")


class MonthlyIncome(BaseModel):
    amount: str = Field(default="N/A", description="Gross monthly income value with currency symbol (e.g., '$6,250.00')")
    confirmed: bool = Field(default=False, description="Whether the income has been confirmed by a third party")
    confirmed_by: str = Field(default="N/A", description="Who confirmed the income (e.g., 'HR', 'supervisor')")


class LeaseApplication(BaseModel):
    applicant_name: str = Field(default="N/A", description="Full name of the applicant as written on the form")
    applicant_email: str = Field(default="N/A", description="Contact email address of the applicant")
    unit_id: str = Field(default="N/A", description="Requested unit code or ID (e.g., Apt #402, UNIT 402, Studio Room)")
    monthly_rent: MonthlyRent = Field(default_factory=MonthlyRent, description="Base monthly rent broken into written form and numeric amount")
    monthly_income: MonthlyIncome = Field(default_factory=MonthlyIncome, description="Gross monthly income with confirmation details")
    pet_ownership: bool = Field(default=False, description="Whether the applicant has declared owning any pets")
    pets: Pets = Field(default_factory=Pets, description="Details about the pets declared by the applicant, including quantity and specific information for each pet")
    additional_comments: str = Field(default="N/A", description="Applicant declared comments, footnotes, or any additional notes on the form. However do not repeat information already captured in other fields (e.g., pet details, income confirmation). This field should only include unique information that is not already captured elsewhere in the structured data.")