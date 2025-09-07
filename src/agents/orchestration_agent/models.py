from pydantic import BaseModel

class GetHumanInTheLoopInput(BaseModel):
    """Input for getting more information"""
    question: str


class GetHumanInTheLoopOutput(BaseModel):
    """Response for getting more information"""
    answer: str
