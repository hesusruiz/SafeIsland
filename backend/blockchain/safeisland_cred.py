import os
import time
import sqlite3
import json
import uuid as unique_id
from sqlite3.dbapi2 import Connection
from eth_utils.crypto import keccak
from hexbytes import HexBytes
from dataclasses import dataclass

from pydantic import BaseModel
from typing import Optional, Tuple

from web3.main import Web3

from blockchain import trustframework as tf
from blockchain import wallet

from jwcrypto import jwt, jwk, jws
from jwcrypto.common import base64url_decode, base64url_encode, json_decode, json_encode


CURRENT_DIR = os.getcwd()
DATABASE_DIR = os.getcwd()
DATABASE_NAME = os.path.join(DATABASE_DIR, "safeislandcred.sqlite")
COVIDCRED_TEMPLATE = os.path.join(CURRENT_DIR, "statictest", "SafeIslandCovidTestResult.json")

table_schema = """
DROP TABLE IF EXISTS safeislandcred;

CREATE TABLE safeislandcred (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  uuid TEXT UNIQUE NOT NULL,
  cert TEXT NOT NULL
);
"""


def get_db() -> Connection:
    db = sqlite3.connect(DATABASE_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    return db


def erase_db() -> Connection:
    """Erase the Covid19 table

    """

    # Connect the database (in case of SQLite just opens the file)
    db = get_db()

    # Erase and create the table from scratch
    print(f"\n==> Creating the database schema")
    db.executescript(table_schema)
    print(f"Database schema created")

    return db


def new_certificate(uuid: str, certificate: str) -> str:

    db = get_db()

    db.execute(
        'REPLACE INTO safeislandcred (uuid, cert) VALUES (?, ?)',
        (uuid, certificate)
    )
    # Commit database, just in case
    db.commit()

    # Return certificate id to caller
    return uuid


def certificate(uuid: str) -> str:

    db = get_db()

    cert = db.execute(
        'SELECT * FROM safeislandcred WHERE uuid = ?', (uuid,)
    ).fetchone()

    if cert is None:
        return None

    # Get the serialized format of the certificate
    cert = cert["cert"]

    return cert


def list_certificates():

    db = get_db()

    certs = db.execute('SELECT * FROM safeislandcred ORDER BY id').fetchall()

    return certs


def new_unsigned_credential(
    passenger_first_name: str,
    passenger_last_name: str,
    passenger_id_number: str,
    passenger_date_of_birth: str,
    analysis_id: str,
    analysis_ver: str,
    analysis_date: str,
    analysis_type: str,
    analysis_result: str,
    lab_name: str,
    lab_address: str,
    lab_phone: str,
    issuer_did: str
):
    """Create a Claims object for a Verifiable Credentia in JWT format.
    The returned object has just the plain claims object, and has to be
    signed later.
    """

    # Generate a random UUID, not related to anything in the credential
    # This is important for privacy reasons to avoid possibility of
    # correlation if the UUID is used for Revocation Lists in a blockchain
    uid = unique_id.uuid4().hex

    # Current time and expiration
    now = int(time.time())
    exp = now + 6*24*60*60  # The token will expire in 6 days

    # Generate a template Verifiable Credential
    credential = {
        "iss": issuer_did,
        "sub": passenger_id_number,
        "iat": now,
        "exp": exp,
        "uuid": uid,
        "vc": {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://alastria.github.io/identity/credentials/v1",
                "https://safeisland.org/.well-known/w3c-covid-test/v1"
            ],
            "type": [
                "VerifiableCredential",
                "AlastriaVerifiableCredential",
                "SafeIslandCovidTestResult"
            ],
            "credentialSubject": {
                "covidTestResult": {
                    "analysis": {
                        "id": analysis_id,
                        "ver": analysis_ver,
                        "date": analysis_date,
                        "type": analysis_type,
                        "result": analysis_result
                    },
                    "patient": {
                        "name": passenger_last_name.upper() + "/" + passenger_first_name.upper(),
                        "idnumber": passenger_id_number,
                        "dob": passenger_date_of_birth
                    },
                    "lab": {
                        "name": lab_name,
                        "address": lab_address,
                        "phone": lab_phone
                    },
                    "comments": "These are some comments"
                },
                "issuedAt": ["redt.alastria"],
                "levelOfAssurance": 2
            }
        }
    }

    return credential


def new_signed_credential(claims=None, jwk_key=None):
    """Create a Verifiable Credential in signed JWT format.
    Receives a claims object and a signing key in JWK format
    """

    # Get the issuer from the unsigned credential
    issuer_did = claims["iss"]

    # Try to resolve the Issuer and get its DID Document
    DID, name, DIDDocument, active = tf.resolver.resolveDID(issuer_did)

    # Check if the Issuer exists and return if not
    if DIDDocument is None:
        return None

    # Check if the DID inside the DIDDocument is the same as the one resolved
    if DIDDocument["id"] != issuer_did:
        return None

    import pprint
    pprint.pprint(DIDDocument)
    # Get the public Key from the DID Document
    did_key = DIDDocument["verificationMethod"][0]

    # We should create the signed JWT from the "raw" credential

    # The header of the JWT, specifying the ES256K algorithm
    header = {
        "typ": "JWT",
        "alg": "ES256K",
        "kid": did_key["id"]
    }

    # Generate a JWT token, not yet signed
    token = jwt.JWT(
        algs=["ES256K"],
        header=header,
        claims=claims
    )

    # Sign the JWT with the key
    token.make_signed_token(jwk_key)

    # Serialize the token for transmission or storage
    st = token.serialize()

    return st


def m_new_certificate(
    passenger_first_name: str,
    passenger_last_name: str,
    passenger_id_number: str,
    passenger_date_of_birth: str,
    analysis_id: str,
    analysis_ver: str,
    analysis_date: str,
    analysis_type: str,
    analysis_result: str,
    lab_name: str,
    lab_address: str,
    lab_phone: str,
    issuer_did: str,
    issuer_password: str
):
    """Creates a new certificate.

    --- Definitions ---
    {"name": "passenger_first_name", "prompt": "Passenger first name", "default": "Alberto"}
    {"name": "passenger_last_name", "prompt": "Passenger last name", "default": "Costa"}
    {"name": "passenger_id_number", "prompt": "Document ID number", "default": "46106508H"}
    {"name": "passenger_date_of_birth", "prompt": "Passenger Date of Birth", "default": "27-04-1982"}
    {"name": "analysis_id", "prompt": "Diagnostic number", "default": "LE4RDS"}
    {"name": "analysis_ver", "prompt": "Diagnostic version", "default": "1"}
    {"name": "analysis_date", "prompt": "Diagnostic date", "default": "Now"}
    {"name": "analysis_type", "prompt": "Diagnostic type", "default": "Virolens"}
    {"name": "analysis_result", "prompt": "Result of diagnosis", "default": "FREE"}
    {"name": "lab_name", "prompt": "Laboratory name", "default": "Perfect Health plc"}
    {"name": "lab_address", "prompt": "Laboratory address", "default": "Wonderful Street 123, Perfect City, Valhalla"}
    {"name": "lab_phone", "prompt": "Laboratory phone", "default": "+3463540040"}
    {"name": "issuer_did", "prompt": "DID of Issuer", "default": "did:elsi:VATES-X12345678X"}
    {"name": "password", "prompt": "Password of Issuerr", "default": "ThePassword"}
    """

    # Data to be included for the UK (as 16-Jan-2021)
    #   Name, which should match the name on the travel documents
    #   Date of birth or age
    #   The result of the test
    #   The date the test sample was collected or received by the test provider
    #   The name of the test provider and their contact details
    #   The name of the test device

    if analysis_date == "Now":
        analysis_date = int(time.time())

    # Create a credential with the diagnostic data
    claims = new_unsigned_credential(
        passenger_first_name,
        passenger_last_name,
        passenger_id_number,
        passenger_date_of_birth,
        analysis_id,
        analysis_ver,
        analysis_date,
        analysis_type,
        analysis_result,
        lab_name,
        lab_address,
        lab_phone,
        issuer_did
    )

    # Get the JWK key from the wallet
    key = wallet.key_JWK(issuer_did, issuer_password)
    if key is None:
        print("Error: key from wallet is None!")
        return None
    print(type(key))


    # Create a signed Verifiable Credential in serialized JWT/JWS format
    # Assume the issuer is the Lanzarote Airport, subject is the citizen and should use her ID
    # Assume also that the password is the default one
    st = new_signed_credential(
        claims=claims,
        jwk_key=key
    )

    # Save the Credential in the database, indexed by its unique id
    hash = new_certificate(claims["uuid"], st)
    print(f"New certificate created: {st}")


def m_certificate(
        uuid: str):
    """Gets certificate from its Unique ID.

    --- Definitions ---
    {"name": "uuid", "prompt": "Unique number of certificate", "default": "None"}
    """

    # Check if unique ID was provided
    if uuid == "None":
        print("Error: Must supply a Unique ID")
        return

    # Get the serialized JWT from the database
    cert = certificate(uuid)
    if cert is None:
        print(f"Certificate not found")
        return

    claims = verify_cert_token(cert)
    if claims is None:
        print("Verification of token failed")
        return

    payl = claims
    print(type(payl))

    print(json.dumps(payl, indent=6))


def m_list_certificates():
    """List Covid19 certificates

    """

    certs = list_certificates()
    for cert in certs:
        print(f"\nUnique ID: {cert['uuid']}")
        print(f"   {cert['cert']}")


def verify_cert_token(cert_token:str) -> dict:
    """In order to verify the signature of the JWT, we need first to get the public key that was used.
    The JWT is now in serialized format, so we need:
    1. Deserialize the JWT without verifying it (we do not yet have the public key)
    2. Get the 'kid' property from the header (the JOSE header of the JWT)
    3. The 'kid' has the format did#id where 'did' is the DID of the issuer and 'id' is the 
        identifier of the key in the DIDDocument associated to the DID
    4. Perform resolution of the DID of the issuer
    5. Get the public key specified inside the DIDDocument
    6. Verify the JWT using the public key associated to the DID
    7. Verify that the DID in the 'iss' field of the JWT payload is the same as the one that
        signed the JWT
    """

    # 1. Deserialize the JWT without verifying it (we do not yet have the public key)
    cert_obj = jwt.JWT()
    cert_obj.deserialize(jwt=cert_token)
 
    # Get the protected header of the JWT
    header = cert_obj.token.jose_header

    # 2. Get the 'kid' property from the header (the JOSE header of the JWT)
    key_id = str(header["kid"])

    # 3. The 'kid' has the format did#id where 'did' is the DID of the issuer and 'id' is the 
    #     identifier of the key in the DIDDocument associated to the DID
    key_components = key_id.split("#")
    if len(key_components) != 2:
        print(f"KeyID in JOSE header invalid: {header}")
        return None

    # Get the DID component
    DID = key_components[0]

    # 4. Perform resolution of the DID of the issuer, and get the public key
    _DID, name, didDoc, active = tf.resolver.resolveDID(DID)
    if didDoc is None:
        print(f"No DIDDoc found for DID: {DID}")
        return None

    # 5. Get the public key specified inside the DIDDocument
    keys = didDoc["verificationMethod"]
    publicKeyJwk = None
    for key in keys:
        if key["id"] == key_id:
            publicKeyJwk = key["publicKeyJwk"]

    if publicKeyJwk is None:
        print(f"Key ID not found in DIDDoc: {key_id}")
        return None

    jwk_key = jwk.JWK(**publicKeyJwk)

    # 6. Verify the JWT using the public key associated to the DID
    cert_obj = jwt.JWT(
        jwt=cert_token,
        key=jwk_key,
        algs=["ES256K"]
    )

    # 7. Verify that the DID in the 'iss' field of the JWT payload is the same as the one that
    #     signed the JWT
    claims = json_decode(cert_obj.claims)
    if claims["iss"] != DID:
        print(f"Token issuer is not the same as specified in the header")
        return None

    return claims


















###########################################################
# OLD CODE


def new_signed_credential_old(iss=None, sub=None, certificate=None, password=None):

    # Try to resolve the Issuer and get its DID Document
    DID, name, DIDDocument, active = tf.resolver.resolveDID(iss)

    # Check if the Issuer exists and return if not
    if DIDDocument is None:
        return None

    # Get the public Key from the DID Document
    did_key = DIDDocument["publicKey"][0]

    # Generate a template Verifiable Credential
    now = int(time.time())
    validity = 5*24*60*60  # The token will expire in 6 days
    credential = {
        "iss": iss,
        "sub": sub,
        "iat": now,
        "exp": now + validity,
        "vc": {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://alastria.github.io/identity/credentials/v1",
                "https://safeisland.org/.well-known/w3c-covid-test/v1"
            ],
            "type": [
                "VerifiableCredential",
                "AlastriaVerifiableCredential",
                "SafeIslandCovidTestResult"
            ],
            "credentialSubject": {
                "issuedAt": "alastria.redt",
                "levelOfAssurance": 2,
                "covidTestResult": {
                }
            }
        }
    }

    # Fill the "covidTestResult" field of the Verifiable Credential
    credential["vc"]["credentialSubject"]["covidTestResult"] = certificate

    # The header of the JWT
    header = {
        "typ": "JWT",
        "alg": "ES256K",
        "kid": did_key["id"]
    }

    # Generate a JWT token, not yet signed
    token = jwt.JWT(
        algs=["ES256K"],
        header=header,
        claims=credential
    )

    # Get the JWK key from the wallet
    key = wallet.key_JWK(DID, password)
    if key is None:
        return None
    print(type(key))

    # Sign the JWT with the key
    token.make_signed_token(key)

    # Serialize the token for transmission or storage
    st = token.serialize()

    return st


def new_unsigned_credential_old(
    diagnostic_number,
    diagnosis,
    passenger_first_name: str,
    passenger_last_name: str,
    passenger_id_type: str,
    passenger_id_number: str,
    passenger_phone: str,
    passenger_email: str
):

    ct = {
        "ISSUER_ID": "9012345JK",
        "MERCHANT": {
            "MERCHANT_DATA": {
                "MERCHANT_ID": "did:elsi:VATES-A86212420",
                "MERCHANT_ADDR": "LANZAROTE AIRPORT T1"
            },
            "OPERATOR_DATA": {
                "OPERATOR_ID": "36926766J",
                "OPERATOR_CELL_PHONE_ID": "0034679815514",
                "OPERATOR_CELL_PHONE_GPS": "28.951146, -13.605760"
            },
            "DEVICE_ID": "34567867",
            "CARTRIDGE": {
                "CARTRIDGE_ID": "VRL555555666",
                "CARTRIDGE_DUE_DATE": "24/12/2021"
            }
        },
        "CITIZEN": {
            "NAME": passenger_last_name.upper() + "/" + passenger_first_name.upper(),
            "ID_TYPE": passenger_id_type.upper(),
            "VALID_ID_NUMBER": passenger_id_number,
            "CITIZEN_CELL_PHONE": passenger_phone,
            "CITIZEN_EMAIL_ADDR": passenger_email
        },
        "DIAGNOSTIC_PASS_DATA": {
            "DIAGNOSTIC_NUMBER": diagnostic_number,
            "DIAGNOSTIC_TYPE": "VIROLENS SALIVA",
            "TIMESTAMP": "2020-10-15 11:05:47.659",
            "DIAGNOSIS": diagnosis,
            "DIAGNOSIS_DUE_DATE": "2020-10-17 11:05:47.659",
            "DIAGNOSIS_QR": "",
            "DIAGNOSTIC_PASS_BCK_HASH": ""
        },
        "ACQUIRER_ID": ""
    }

    return ct



