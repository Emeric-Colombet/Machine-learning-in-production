"""API definition for churn detection."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from chaos.domain.customer import Customer, load_churn_model, ModelNotLoaded
from chaos.infrastructure.customer_loader import CustomerLoader
from typing import Optional, Literal
from datetime import datetime, date
from sqlalchemy.exc import OperationalError
from enum import Enum, IntEnum
import loguru
import uuid

description = """
### Churn detection API will help you to detect churners. 🚀


#### Users

You will be able to:

* **Detect Churner** (Route #1).
* **Read Customer's features from Id** (Route #2).
* **Detect Churner from Id** (Route #3).
"""

class CustomerInput(BaseModel):
    """Churn detection parameters.

    Parameters
    ----------
    BALANCE : float
        customer bank account balance
    NB_PRODUITS : int
        how many products the customer owns
    CARTE_CREDIT : str ("Yes" or "No")
        'Yes' if the customer has a credit card
    SALAIRE : float
        customer's salary
    SCORE_CREDIT : float
        customer score for credit allocation
    DATE_ENTREE : datetime
        optional (fot futur use), date of the customer subscription
        date in format "YYYY-MM-DD HH:MM"
    PAYS : str
        country of the customer
    SEXE : str
        customer's gender, 'H' (Male) of 'F' (Female)
    AGE : int
        customer's age
    MEMBRE_ACTIF: str ('Yes' or 'No')
        'Yes' if the customer is active on his bank account
    """

    BALANCE: float = None
    NB_PRODUITS: int = None
    CARTE_CREDIT: Literal["Yes", "No"] = None
    SALAIRE: float = None
    SCORE_CREDIT: float = None
    DATE_ENTREE: Optional[datetime] = None
    PAYS: str = None
    SEXE: Literal["H", "F"] = None
    AGE: int = None
    MEMBRE_ACTIF: Literal["Yes", "No"] = None


class BddCustomerOutput(BaseModel):
    ID_CLIENT: int
    DATE_ENTREE: date
    NOM: str
    PAYS: str
    SEXE: str
    AGE: int
    MEMBRE_ACTIF: str
    BALANCE: float
    NB_PRODUITS: int
    CARTE_CREDIT: str
    SALAIRE: float
    SCORE_CREDIT: float
    CHURN: str

class Customer_ids(IntEnum, Enum):
    customer_1 = 15791700
    customer_2 = 15569438
    customer_3 = 15642821
    customer_fake = 123456789


app = FastAPI(
    title="🚀 Churn detection",
    description=description,
    openapi_tags=[{
        "name": "detect",
        "description": ("Give a probability of churn "
                        "given customer's characteristics")},
       {"name": "read id",
        "description": ("Read customer's features from given id")},

       {"name": "detect from id",
        "description": ("Give a probability of churn " 
                        "given customer's id")          
    }]
)

logger = loguru.logger
logger.remove()
logger.add('logs/logs.logs', format="{time} - {level} - ({extra[request_id]}) {message} ", level="DEBUG")

HTTP_NOT_FOUND = 404
HTTP_INTERNAL_SERVER_ERROR = 500

@app.exception_handler(ModelNotLoaded)
async def _module_not_found_handler(request: Request, exc: ModelNotLoaded):
    logger.error("Churn is not loaded")
    return JSONResponse(
        status_code=HTTP_INTERNAL_SERVER_ERROR,
        content={'message': "Churn model not loaded"})

@app.exception_handler(OperationalError)
async def _postgressql_connexion__handler(request: Request, exc: OperationalError):
    logger.error("SQL connection not found")
    return JSONResponse(
        status_code=HTTP_INTERNAL_SERVER_ERROR,
        content={'message': "No SQL connection"})

class UnicornException(Exception):
    def __init__(self, customer_id:int):
        self.customer_id =customer_id

@app.exception_handler(UnicornException)
async def unicorn_exception_handler(request: Request, exc: UnicornException):
    logger.error(f"Client ID {exc.customer_id} not found")
    return JSONResponse(status_code = HTTP_NOT_FOUND,
                        content = {'message' : f"Client ID {exc.customer_id} not found" })


class Answer(BaseModel):
    """Churn detection response."""

    answer: float


CHURN_MODEL_NOT_FOUND = -1
CHURN_MODEL = None

@app.middleware("http")
async def request_middleware(request, call_next):
    request_id = str(uuid.uuid4())
    with logger.contextualize(request_id=request_id):
        logger.info("Request started")

        try:
            response = await call_next(request)

        finally:
            logger.info(f"Request status code : {response.status_code}")
            logger.info("Request ended")
            return response


@app.on_event("startup")
async def startup_event():
    """Load model just once."""
    global CHURN_MODEL
    CHURN_MODEL = None
    try:
        CHURN_MODEL = load_churn_model()
    except ModelNotLoaded:
        logger.error("No model loaded")


@app.post("/detect/", tags=["detect"])
def detect(customer_input: CustomerInput):
    """Call Customer model churn detection.

    Parameters
    ----------
    customer_input : CustomerInput(BaseModel)
        Customer marketing characterics
    """
    customer = Customer(customer_input.dict(), CHURN_MODEL)

    answer = customer.predict_subscription()

    return Answer(answer=answer)


@app.get("/customer/{customer_id}", tags=["read id"])
def read_item(customer_id : Customer_ids):
    result_ = CustomerLoader().does_the_ID_exist(customer_id)    
    if not result_:
        raise UnicornException(customer_id=customer_id)
    customer_loader = CustomerLoader()
    df_prospect = customer_loader.find_a_customer(customer_id)
    dict_prospect = df_prospect.to_dict(orient="records")[0]
    bdd_customer_output = BddCustomerOutput(**dict_prospect)
    return bdd_customer_output

@app.get("/customer_detect/{customer_id}", tags=["detect from id"])
def detect_item(customer_id: Customer_ids):
    """Detect churn from customer id.

    Parameters
    ----------
    customer_id : client ID

    """
    result_ = CustomerLoader().does_the_ID_exist(customer_id)
    if not result_:
        raise UnicornException(customer_id=customer_id)
    customer_loader = CustomerLoader()
    load_customer = customer_loader.find_a_customer(customer_id)
    load_customer.drop(columns=['CHURN'])
    dict_customer = load_customer.to_dict(orient="records")[0]
    customer = Customer(dict_customer, CHURN_MODEL)

    answer = customer.predict_subscription()

    return Answer(answer=answer)
