FROM ghcr.io/cirruslabs/flutter:stable AS build

WORKDIR /app
COPY . /app

RUN flutter pub get
RUN flutter build web --release

FROM nginx:alpine

COPY --from=build /app/build/web /usr/share/nginx/html

EXPOSE 80
