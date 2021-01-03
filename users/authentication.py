from rest_framework import authentication


class BearerAuthentication(authentication.TokenAuthentication):
    """
    Simple token based authentication using username and password

    Clients should authenticate by passing the token key in the 'Authorization'
    HTTP header, prepended with the string 'Bearer '.  For example:

    Authorization: Bearer 956e252a-513c-48c5-92dd-bfddc364e812
    """
    keyword = 'Bearer'
