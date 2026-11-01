from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data.update(
            {
                "id": user.pk,
                "email": user.email,
                "username": user.username,
                "role": user.role,
            }
        )
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refresh_token = RefreshToken(serializer.validated_data["refresh"])
        except TokenError as exc:
            raise InvalidToken(str(exc)) from exc

        token_user_id = refresh_token.get(api_settings.USER_ID_CLAIM)
        if str(token_user_id) != str(request.user.pk):
            raise PermissionDenied("You can only revoke your own refresh token.")

        refresh_token.blacklist()
        return Response({"detail": "Refresh token blacklisted."})


class ProfileStatsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        return Response(
            {
                "email": user.email,
                "role": user.role,
                "is_staff": user.is_staff,
                "date_joined": user.date_joined,
            }
        )
