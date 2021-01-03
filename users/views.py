import logging
from rest_framework import status
from rest_framework import generics
from users.serializers import UserSerializer, UserCreateSerializer, LoginResponseSerializer
from rest_framework import parsers, renderers
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.compat import coreapi, coreschema
from rest_framework.response import Response
from rest_framework.schemas import ManualSchema
from rest_framework.views import APIView
from drf_yasg2.utils import swagger_auto_schema
logger = logging.getLogger(__name__)


class ObtainAuthToken(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser,)
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = AuthTokenSerializer
    if coreapi is not None and coreschema is not None:
        schema = ManualSchema(
            fields=[
                coreapi.Field(
                    name="username",
                    required=True,
                    location='form',
                    schema=coreschema.String(
                        title="Username",
                        description="Valid username for authentication",
                    ),
                ),
                coreapi.Field(
                    name="password",
                    required=True,
                    location='form',
                    schema=coreschema.String(
                        title="Password",
                        description="Valid password for authentication",
                    ),
                ),
            ],
            encoding="application/json",
        )

    @swagger_auto_schema(request_body=AuthTokenSerializer, responses={200: LoginResponseSerializer})
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})


class Register(generics.CreateAPIView):
    """
    Create a user who can create trips

    {
        "email": "bob_marley@gmail.com",
        "first_name": "Bob",
        "last_name": "Marley",
        "phone_no": "123123123",
    }
    """
    serializer_class = UserCreateSerializer
    authentication_classes = []
    permission_classes = []


class Logout(APIView):

    def get(self, request, format=None):
        # simply delete the token to force a login
        request.user.auth_token.delete()
        resp = dict({
            "message": "Successfully Logout"
        })
        return Response(resp, status=status.HTTP_200_OK)


class Profile(generics.RetrieveUpdateAPIView):
    """
    Get and update profile data. This data will be
    set during User registration.

    Update profile:
    {
        "first_name": "Bob",
        "last_name": "Marley",
        "phone_no": "123123123",
    }
    """
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super(Profile, self).update(request, *args, **kwargs)
