from rest_framework import serializers
from users.models import User
from django.db import IntegrityError


class LoginResponseSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=128)


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        exclude = (
            'id',
            'password',
            'is_superuser',
            'is_staff',
            'is_active',
            'date_joined',
            'last_login',
            'groups',
            'user_permissions',
        )
        read_only_fields = (
            'email',
            'is_superuser',
            'is_staff',
            'is_active',
            'date_joined',
            'last_login',
        )


class UserCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, max_length=32)

    class Meta:
        model = User
        exclude = (
            'id',
            'is_superuser',
            'is_staff',
            'is_active',
            'date_joined',
            'last_login',
            'groups',
            'user_permissions',
        )
        read_only_fields = (
            'is_superuser',
            'is_staff',
            'is_active',
            'date_joined',
            'last_login',
        )

    def create(self, validated_data):
        try:
            user = User.objects.create_user(validated_data.pop("email"), validated_data.pop("password"),
                                            **validated_data)
            return user
        except IntegrityError as e:
            error = dict({'error': "User with email already present"})
            raise serializers.ValidationError(error)
