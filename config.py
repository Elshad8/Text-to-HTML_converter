import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "development")
API_KEY = os.getenv("API_KEY")

EDITABLE_PROPERTIES={
    'button':['text','color','background','border','font-size'],
    'input':['placeholder','color','background','border','font-size'],
    'div':['color','background','border','font-size'],
    'p':['text','color','font-size','font-family']

    #Add more elements and tehir editable properties as needed
}