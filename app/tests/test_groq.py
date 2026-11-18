
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv(override=True)

try:
    llm = ChatGroq(
        model=os.getenv("GROQ_MODEL"),
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
        timeout=60,
        max_retries=2
    )

    response = llm.invoke("Reply with exactly GROQ_CONNECTED")
    print("SUCCESS:", response.content)

except Exception as e:
    print("ERROR TYPE:", type(e).__name__)
    print("ERROR DETAILS:", repr(e))
