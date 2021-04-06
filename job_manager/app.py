import logging
from fastapi import FastAPI,BackgroundTasks,Response,Depends

from models import Job,ParsingError,Base
from db import Session,engine
from cache import cache,NotCached
from crud import handle_order

from settings import config

logger = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
logger.setLevel(logging.WARNING)

try:
    logging.basicConfig(level=getattr(logging,config("LOG_LEVEL")))
except AttributeError:
    pass
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)
app = FastAPI()

def get_sess():
    sess = Session()
    try:
        yield sess
    finally:
        sess.close()

@app.get("/{path:path}")
def dispatch(path:str,background_tasks:BackgroundTasks,session = Depends(get_sess)):
    try:
        job = Job.parse_whole_path(path)
    except ParsingError:
        return Response(status_code=404)

    try:
        result = cache.get(job.path())
    except NotCached:
        logger.info("Handling %s",str(job))
        background_tasks.add_task(handle_order,session,path)
        return Response("Handling job",status_code=202)
    else:
        logger.info("Returning %s from cache",str(job))
        return Response(result,media_type="application/octet-stream")