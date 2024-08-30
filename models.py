from pydantic import BaseModel
import tiktoken

class RequestModel(BaseModel):
    prompt: str

class ResponseModel(BaseModel):
    html: str

def count_tokens(messages):
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding("cl100k_base")
    text = ""
    for message in messages:
        if isinstance(message, str):
            text += message
        else:
            text += " ".join([part for part in message if isinstance(part, str)])
    num_tokens = len(encoding.encode(text))
    return num_tokens
