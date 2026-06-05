FROM alpine:3.19

RUN apk add --no-cache dnsmasq

COPY dnsmasq.conf /etc/dnsmasq.conf

EXPOSE 53/udp
EXPOSE 53/tcp

ENTRYPOINT ["dnsmasq", "--no-daemon", "--log-facility=-"]
