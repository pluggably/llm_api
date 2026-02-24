FROM ghcr.io/cirruslabs/flutter:stable AS build

WORKDIR /workspace
COPY frontend /workspace/frontend
COPY clients /workspace/clients

WORKDIR /workspace/frontend
RUN flutter pub get
RUN flutter build web --release

FROM nginx:alpine

COPY --from=build /workspace/frontend/build/web /usr/share/nginx/html

EXPOSE 80
