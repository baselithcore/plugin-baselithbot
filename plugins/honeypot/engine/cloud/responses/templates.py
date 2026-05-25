"""AWS Response Templates and Constants.

Error response templates and constants for AWS API simulation.
"""

# AWS Error Response Templates
AWS_ERROR_TEMPLATES = {
    # Authentication errors
    "InvalidClientTokenId": {
        "code": "InvalidClientTokenId",
        "message": "The security token included in the request is invalid.",
        "http_status": 403,
    },
    "ExpiredToken": {
        "code": "ExpiredToken",
        "message": "The security token included in the request is expired",
        "http_status": 403,
    },
    "SignatureDoesNotMatch": {
        "code": "SignatureDoesNotMatch",
        "message": "The request signature we calculated does not match the signature you provided. Check your AWS Secret Access Key and signing method.",
        "http_status": 403,
    },
    "MissingAuthenticationToken": {
        "code": "MissingAuthenticationToken",
        "message": "Request is missing Authentication Token",
        "http_status": 403,
    },
    # Authorization errors
    "AccessDenied": {
        "code": "AccessDenied",
        "message": "User: arn:aws:iam::{account_id}:user/{username} is not authorized to perform: {action} on resource: {resource}",
        "http_status": 403,
    },
    "UnauthorizedAccess": {
        "code": "UnauthorizedAccess",
        "message": "You are not authorized to perform this operation.",
        "http_status": 403,
    },
    # Resource errors
    "NoSuchBucket": {
        "code": "NoSuchBucket",
        "message": "The specified bucket does not exist",
        "http_status": 404,
    },
    "NoSuchKey": {
        "code": "NoSuchKey",
        "message": "The specified key does not exist.",
        "http_status": 404,
    },
    "NoSuchEntity": {
        "code": "NoSuchEntity",
        "message": "The {entity_type} with name {entity_name} cannot be found.",
        "http_status": 404,
    },
    "ResourceNotFoundException": {
        "code": "ResourceNotFoundException",
        "message": "Secrets Manager can't find the specified secret.",
        "http_status": 404,
    },
    # Validation errors
    "ValidationError": {
        "code": "ValidationError",
        "message": "{message}",
        "http_status": 400,
    },
    "MalformedPolicyDocument": {
        "code": "MalformedPolicyDocument",
        "message": "The policy document is malformed.",
        "http_status": 400,
    },
    "InvalidParameterValue": {
        "code": "InvalidParameterValue",
        "message": "Value ({value}) for parameter {parameter} is invalid.",
        "http_status": 400,
    },
    # Rate limiting
    "Throttling": {
        "code": "Throttling",
        "message": "Rate exceeded",
        "http_status": 429,
    },
    "ServiceUnavailable": {
        "code": "ServiceUnavailable",
        "message": "Service is currently unavailable. Please try again later.",
        "http_status": 503,
    },
}
