from pydantic import BaseModel, conlist
from typing import Optional, List

# User Profiling Question & Response Models
class profileChoiceModel(BaseModel):
    image_id: int
    image_title: str
    
class profileQuestionModel(BaseModel):
    question_id: int
    choices: conlist(profileChoiceModel, min_length=4, max_length=4)
    
class allProfileQuestionModel(BaseModel):
    questions: conlist(profileQuestionModel) 

class profileResponseModel(BaseModel):
    question_id: int
    choice_image_id: int
    choice_image_title: str

class allProfileResponseModel(BaseModel):
    responses: List[profileResponseModel]
    user_name: Optional[str] = None