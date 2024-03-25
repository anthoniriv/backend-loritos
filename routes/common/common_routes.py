from config import app, db
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.get("/getFrequentlyQuestions")
async def get_frequently_questions():
    try:
        collection_ref = db.collection("tDash_frequentQuestions")
        docs = collection_ref.stream()

        frequent_questions = []

        for doc in docs:
            frequent_questions.append(doc.to_dict())

        return JSONResponse(content={"data": frequent_questions}, status_code=200)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener preguntas frecuentes: {str(e)}"
        )
