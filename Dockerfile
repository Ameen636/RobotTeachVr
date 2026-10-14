# RoboTeachVR — static 3D viewer, deployable on Render as a Docker Web Service.
# Serves preview.html (+ RoboTeachVR.glb and screenshots) via nginx.
# Listens on $PORT injected by Render (defaults to 10000 for local runs).

FROM nginx:alpine

# Static web assets
COPY preview.html /usr/share/nginx/html/preview.html
# Serve the viewer at `/` as well as `/preview.html`
COPY preview.html /usr/share/nginx/html/index.html
COPY RoboTeachVR.glb /usr/share/nginx/html/RoboTeachVR.glb
COPY preview_3d.png /usr/share/nginx/html/preview_3d.png
COPY preview_plan.png /usr/share/nginx/html/preview_plan.png

# Nginx vhost template. The base image's docker-entrypoint.d/20-envsubst-on-templates.sh
# renders every /etc/nginx/templates/*.template with envsubst on start,
# so ${PORT} is resolved at container boot (Render injects it).
COPY default.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 10000

# Inherited ENTRYPOINT (/docker-entrypoint.sh) + CMD ("nginx -g 'daemon off;'") apply.
