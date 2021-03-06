import sirius_sdk
from django.conf import settings
from main.ssi.custom import RedisLogger, fetch_schema


async def check_driver_license(connection_key: str, pairwise: sirius_sdk.Pairwise) -> (bool, dict):
    proof_request = {
        "nonce": await sirius_sdk.AnonCreds.generate_nonce(),
        "name": "Verify the drive license",
        "version": "1.0",
        "requested_attributes": {
            "attr1_referent": {
                "name": "categories",
                "restrictions": {
                    "issuer_did": settings.POLICE["DID"]
                }
            },
            "attr2_referent": {
                "name": "last_name",
                "restrictions": {
                    "issuer_did": settings.POLICE["DID"]
                }
            },
            "attr3_referent": {
                "name": "first_name",
                "restrictions": {
                    "issuer_did": settings.POLICE["DID"]
                }
            }
        }
    }

    ledger = await sirius_sdk.ledger(settings.DKMS_NAME)
    logger = RedisLogger(connection_key)
    verifier = sirius_sdk.aries_rfc.Verifier(pairwise, ledger, logger=logger)
    ok = await verifier.verify(proof_request=proof_request, comment="Verify driver license")
    if ok:
        return ok, verifier.revealed_attrs
    else:
        return ok, None


async def issue_confirmation(connection_key: str, pairwise: sirius_sdk.Pairwise, values: dict):
    cred_def, schema = await fetch_schema(
        name="Vehicle license",
        version="1.0",
        attrs=[
            "last_name",
            "first_name",
            "pick_up_date",
            "drop_off_date",
            "car_name",
            "car_reg_number"
        ],
        did=settings.RENT_A_CAR["DID"]
    )
    logger = RedisLogger(connection_key)
    issuer = sirius_sdk.aries_rfc.Issuer(pairwise, logger=logger)
    preview = [sirius_sdk.aries_rfc.ProposedAttrib(key, str(value)) for key, value in values.items()]
    translation = [
        sirius_sdk.aries_rfc.AttribTranslation("last_name", "Last Name"),
        sirius_sdk.aries_rfc.AttribTranslation("first_name", "First Name"),
        sirius_sdk.aries_rfc.AttribTranslation("pick_up_date", "Pick-up date"),
        sirius_sdk.aries_rfc.AttribTranslation("drop_off_date", "Drop-off date"),
        sirius_sdk.aries_rfc.AttribTranslation("car_name", "Car name"),
        sirius_sdk.aries_rfc.AttribTranslation("car_reg_name", "Vehicle registration number")
    ]

    await issuer.issue(
        values=values,
        schema=schema,
        cred_def=cred_def,
        preview=preview,
        translation=translation,
        comment="Here is your vehicle license",
        locale="en"
    )
