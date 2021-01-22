# The Fastapi web server
from fastapi import FastAPI, status, HTTPException, Body, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# JWT support
from jwcrypto.common import JWException

# Import uvicorn for debugging
import uvicorn

# For the data models
from typing import Dict, Optional, cast
from pydantic import BaseModel, BaseSettings

# For connecting to the blockchain
from blockchain import trustframework as tf
from blockchain import wallet, certificates, didutils

# SQLite for storing persistent data
import sqlite3

# A very fast cache with expiration: https://github.com/tkem/cachetools/
from cachetools import TTLCache


#####################################################
# CONFIGURE THE SERVER
#####################################################

class Settings(BaseSettings):
    MAX_CONTENT_LENGTH: int = 30000
    TTLCACHE_NUM_ELEMENTS: int = 10000
    TTLCACHE_EXPIRATION: int = 60
    BLOCKCHAIN_NODE_IP: str = tf.BLOCKCHAIN_NODE_IP_PRODUCTION

settings = Settings()
app = FastAPI(
    title="EBSI-Alastria Identity APIs",
    description="SSI and Verifiable Credentials with interoperability EBSI-Alastria Red T",
    version="0.9.0",
    openapi_url="/api/v1/openapi.json"
)

tags_metadata = [
    {
        "name": "DID resolution",
        "description": "Operation to resolve a DID.",
    },
    {
        "name": "Wallet and Identities",
        "description": "Operations to create and manage identities.",
    },
    {
        "name": "EBSI-style Verifiable Credentials",
        "description": "Operations related to Verifiable Credentials.",
    },
    {
        "name": "EBSI-style Trusted Issuers registry",
        "description": "Operations related to Trusted Issuers.",
    },
    {
        "name": "Secure Messaging Server",
        "description": "Operations to securely send&receive credentials between participants.",
    },
    {
        "name": "Server Health Status",
        "description": "To check if the server is working.",
    },
]



app.mount("/static", StaticFiles(directory="statictest"), name="static")

templates = Jinja2Templates(directory="templates")

# Create the cache for messaging credentials
c = TTLCache(settings.TTLCACHE_NUM_ELEMENTS, settings.TTLCACHE_EXPIRATION)

# Create another cache for 100 DID Documents for 3 hours
doc_cache = TTLCache(100, 3*60*60)

# Connect to blockchain when starting the server
tf.connect_blockchain()


#####################################################
# VERIFIER APIS
#####################################################

# The reply messaje
class DIDDocument_reply(BaseModel):
    payload: Dict
    class Config:
        schema_extra = {
            "example": {
                "@context": [
                    "https://www.w3.org/ns/did/v1",
                    "https://w3id.org/security/v1"
                ],
                "id": "did:elsi:VATES-B60645900",
                "publicKey": [
                    {
                        "id": "did:elsi:VATES-B60645900#key-verification",
                        "type": "JwsVerificationKey2020",
                        "controller": "did:elsi:VATES-B60645900",
                        "publicKeyJwk": {
                            "kid": "key-verification",
                            "kty": "EC",
                            "crv": "secp256k1",
                            "x": "QoHDiX_hLAm7M__qUyCXRod6jzx0tCxS-_RoIjP1xzg",
                            "y": "Tqp4fFlMb6YcW-3b86kKjcpx8TyIg4Mkb5Q3nB5bgq4"
                        }
                    }
                ],
                "service": [
                    {
                        "id": "did:elsi:VATES-B60645900#info",
                        "type": "EntityCommercialInfo",
                        "serviceEndpoint": "www.in2.es",
                        "name": "IN2"
                    }
                ],
                "alaExtension": {
                    "redT": {
                        "domain": "in2.ala",
                        "ethereumAddress": "0x202e88FA672F65810e5Ed0EF84fFe919063d4E60"
                    }
                },
                "created": "2020-12-23T13:35:23Z",
                "updated": "2020-12-23T13:35:23Z"
            }
        }


# Resolves a DID and returns the DID Document (JSON format), if it exists
# We support four DID methods: ebsi, elsi, ala, peer.
@app.get("/api/did/v1/identifiers/{DID}", response_model=DIDDocument_reply, tags=["DID resolution"])
def resolve_DID(DID: str):

    # Check if the DID is already in the cache
    didDoc = cast(dict, doc_cache.get(DID))
    if didDoc is not None:
        return {"payload": didDoc}
   
    # Parse the DID if it is one of the supported types
    err, did_struct = didutils.parseDid(DID)
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    # Process ELSI DID method
    if did_struct == "elsi":

        # Try to resolve from the blockchain node
        _DID, name, didDoc, active = tf.resolver.resolveDID(DID)
        if didDoc is None:
            return {"payload": ""}

        # Store the DID and associated DIDDocument in the cache
        doc_cache[DID] = didDoc

        return {"payload": didDoc}

    # Process EBSI DID method
    if did_struct == "ebsi":

        # When EBSI reaches production, we will resolve the DID using the API
        # which now is at: https://api.ebsi.xyz/did/v1/identifiers/{did}
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not implemented")

    # Process AlastriaID DID method
    if did_struct == "ala":

        # When AlastriaID (standard) reaches production, we will resolve the DID
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not implemented")

    # Process Peer DID method
    if did_struct == "peer":

        # TODO: implement the Peer DID
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not implemented")

    # Should not reach here
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="DID parsing failed")

    

# Lists the Trusted Issuers in the system
@app.get("/api/trusted-issuers-registry/v1/issuers", tags=["EBSI-style Trusted Issuers registry"])
def list_trusted_issuers():

    trusted_issuers = tf.dump_trusted_identities()

    return {"payload": trusted_issuers}


#####################################################
# APIS FOR USAGE BY THE VERIFIER MOBILE APP
#####################################################

# The message that is sent or received, with an opaque payload (but must be string)
class VerifyJWTMessage(BaseModel):
    payload: str
    class Config:
        schema_extra = {
            "example": {
                "payload": "JWT representation as JWS Compact Serialization in RFC 7519"
            }
        }


# Verify a credential, received as a JWT
@app.post("/api/verifiable-credential/v1/verifiable-credential-validations", tags=["EBSI-style Verifiable Credentials"])
def credential_verify(msg: VerifyJWTMessage):

    # Check if we have received some data in the POST
    jwt_cert = msg.payload
    if len(jwt_cert) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No data received")

    # Verify the certificate
    try:
        claims = certificates.verify_cert_token(jwt_cert)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.args)
    
    if claims is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification of token failed")

    return {"payload": claims}


#####################################################
# APIS FOR USAGE BY THE ISSUER MOBILE APP
#####################################################


# Get a list of credentials from the database in the server in JSON
@app.get("/api/verifiable-credential/v1/credentials", tags=["EBSI-style Verifiable Credentials"])
def credential_listjson():
    rows = certificates.list_certificates()
    certs = []
    for row in rows:
        certs.append(row["diag_id"])

    return {"payload": certs}


# Gets a credential (JSON) from issuer by specifying its uniqueID
@app.get("/api/verifiable-credential/v1/{uniqueID}", tags=["EBSI-style Verifiable Credentials"])
def credential_get(uniqueID: str):
    cert = certificates.certificate(uniqueID)
    return {"payload": cert}

# Gets a credential (JSON) from issuer by specifying its uniqueID
@app.get("/api/verifiable-credential/v2/{uniqueID}", tags=["EBSI-style Verifiable Credentials"])
def credential_get2(uniqueID: str):
    cert_struct = certificates.certificate2(uniqueID)
    return {"payload": cert_struct}


#####################################################
# CREATE AN IDENTITY
#####################################################

# The input message
class CreateIdentity_request(BaseModel):
    DID: str                    # ELSI DID of the new identity, example: "did:elsi:VATES-B60645900"
    domain_name: str            # Blockchain domain name to assign, example: "in2.ala"
    website: str                # Website of the entity, example: "www.in2.es"
    commercial_name: str        # Commercial name, example: "IN2 Innovating 2gether"
    parent_node_account: str    # Account that owns the parent node, example: "Alastria"
    password: str               # Password to encrypt private key, example: "ThePassword"

    class Config:
        schema_extra = {
            "example": {
                "DID": "did:elsi:VATES-B60645900",
                "domain_name": "in2.ala",
                "website": "www.in2.es",
                "commercial_name": "IN2 Innovating 2gether",
                "parent_node_account": "Alastria",
                "password": "ThePassword"
            }
        }


# The reply messaje
class CreateIdentity_reply(BaseModel):
    didDoc: Dict


@app.post("/api/did/v1/identifiers", tags=["Wallet and Identities"])
def create_identity(msg: CreateIdentity_request):
    
    # Check if we have received some data in the POST
    if len(msg.DID) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No data received")

    # Create the identity using the library
    error, didDoc = tf.create_identity(
        msg.DID, msg.domain_name, msg.website, msg.commercial_name, msg.parent_node_account, msg.password)
    if error is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return didDoc.to_dict()


#####################################################
# MESSAGING SERVER
#####################################################

# The message that is sent or received, with an opaque payload (but must be string)
class Message(BaseModel):
    payload: str


# Write a payload to the cache associated to a sessionKey
# This API is used to send a Credential to a receiver. It is used by:
# 1. The Issuer when sending a credential to the Passenger
# 2. The Passenger when sending a credential to the Verifier
@app.post("/api/write/{sessionKey}", tags=["Secure Messaging Server"])
def write_item(sessionKey: str, msg: Message):
    
    # Check if we have received some data in the POST
    if len(msg.payload) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No data received")

    # Store in the cache and return the session key
    c[sessionKey] = msg.payload
    return {"sessionKey": sessionKey}


# Read the payload from the cache specifying the unique sessionKey
# This API is used to receive a Credential from a sender. It is used by:
# 1. The Issuer when receiving a credential from the Issuer
# 2. The Verifier when receiving a credential from the Passenger
@app.get("/api/read/{sessionKey}", response_model=Message, tags=["Secure Messaging Server"])
def read_item(sessionKey):

    # Try to get the element from the cache, erasing it if it exists
    payload = c.pop(sessionKey, "")
    return {"payload": payload}


#####################################################
# HEALTH CHECKING
#####################################################
@app.get("/api/ping", tags=["Healh status"])
def ping():
    return {"payload": "Hello, v1.0.1"}





if __name__ == "__main__":
    uvicorn.run("fmain:app", host="127.0.0.1", port=8000, reload=True)