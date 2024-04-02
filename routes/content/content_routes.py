from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from config import db
from models import GetContent

router = APIRouter()


@router.post("/listContent")
async def get_type_content(contentID: GetContent):
    try:
        if contentID.contentTypeId == "UM":
            content_type_id = 1
        else:
            content_type_id = 2

        collection_ref = db.collection("tDash_content")
        docs = collection_ref.where("typeContent", "==", content_type_id).stream()

        content = []

        for doc in docs:
            doc_data = doc.to_dict()
            content_item = {
                "id": doc.id,
                "name": doc_data.get("name", ""),
                "description": doc_data.get("description", ""),
                "typeContent": doc_data.get("typeContent", ""),
                "content": {"listDocuments": [], "listContent": []},
            }

            content_units_ref = doc.reference.collection("tDash_ContentUnits")
            content_units_docs = content_units_ref.stream()

            for unit_doc in content_units_docs:
                unit_doc_data = unit_doc.to_dict()
                if unit_doc_data.get("fileType") == 2:
                    content_item["content"]["listDocuments"].append(unit_doc_data)
                else:
                    content_item["content"]["listContent"].append(unit_doc_data)

            content.append(content_item)

        return JSONResponse(content={"data": content}, status_code=200)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener el contenido: {str(e)}"
        )
