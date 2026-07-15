"""Pydantic output schemas shared by crew.py and main.py."""

from pydantic import BaseModel


class Assumption(BaseModel):
    statement: str
    questionable: bool
    why: str


class AssumptionSet(BaseModel):
    assumptions: list[Assumption]


class Fundamental(BaseModel):
    truth: str
    basis: str


class FundamentalSet(BaseModel):
    fundamentals: list[Fundamental]


class Recommendation(BaseModel):
    recommendation: str
    rests_on: list[str]
