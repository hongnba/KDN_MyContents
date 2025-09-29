import sys, os
import typing

from fastapi import APIRouter
from fastapi import FastAPI, Query, Request
from pydantic import BaseModel
import bson
from bson import ObjectId

from ksubscribe_server.recommand.recommand import reommand_contents

router = APIRouter()

class ContentQuery(BaseModel):
    organization: typing.List[str] = []
    keyword: typing.List[str] = []


class RecommandContents(BaseModel):
    userId: str = ""
    limit: int = 8

@router.post("/recommendByUser")
async def analize_sentense(body: RecommandContents):
    return {"rcmd_contents": reommand_contents(body.userId)}
