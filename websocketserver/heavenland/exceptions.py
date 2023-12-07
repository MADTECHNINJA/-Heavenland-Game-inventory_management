
class JWTDecodeError(Exception):
    """
    raised if the decoding of JWT was not successful
    """


class UnauthorizedError(Exception):
    """
    raised if the request is unauthorized
    """


class HeavenlandAPIError(Exception):
    """
    raised if heavenland API returns an error
    """

    def __init__(self, status_code: int = 400):
        self.status_code = status_code
