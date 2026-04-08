global
  log /dev/log local0
  log /dev/log local1 notice
  daemon

defaults
  log global
  mode tcp
  option tcplog
  option clitcpka
  option srvtcpka
  timeout connect 10s
  timeout client 4h
  timeout server 4h

frontend vxcloud_vless_in
  mode tcp
  option tcplog
  bind ${FRONTEND_BIND_ADDR}:${FRONTEND_PORT}
  default_backend vxcloud_vless_nodes

backend vxcloud_vless_nodes
  mode tcp
  balance leastconn
  option tcp-check
  default-server inter 3s rise 2 fall 3 slowstart 60s
${BACKEND_SERVERS}
