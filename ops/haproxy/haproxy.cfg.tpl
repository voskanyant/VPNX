global
  log /dev/log local0
  log /dev/log local1 notice
  daemon

defaults
  log global
  mode tcp
  option tcplog
  timeout connect 5s
  timeout client 60s
  timeout server 60s

frontend vxcloud_vless_in
  mode tcp
  option tcplog
  bind ${FRONTEND_BIND_ADDR}:${FRONTEND_PORT}
  default_backend vxcloud_vless_nodes

backend vxcloud_vless_nodes
  mode tcp
  balance leastconn
  option tcp-check
${BACKEND_SERVERS}
