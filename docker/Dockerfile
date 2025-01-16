ARG BASE_IMAGE=ubuntu:20.04
FROM $BASE_IMAGE

LABEL maintainer="molly_developer"
ENV LANG C.UTF-8
ENV TimeZone=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TimeZone /etc/localtime && echo $TimeZone > /etc/timezone
