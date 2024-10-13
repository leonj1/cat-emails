from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from gmail_categorizer import get_imap_client, process_email

app = FastAPI()

class EmailResponse(BaseModel):
    status: str
    category: str

@app.post("/process_email/{msg_id}", response_model=EmailResponse)
async def process_email_endpoint(msg_id: int):
    client = get_imap_client()
    try:
        action_taken, details = process_email(client, msg_id)
        return EmailResponse(status=action_taken, category=details)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.logout()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
