FROM busybox:1.36

ARG GGUF_FILENAME
ENV GGUF_FILENAME=${GGUF_FILENAME}

COPY ${GGUF_FILENAME} /model/${GGUF_FILENAME}

CMD sh -c '\
  if [ ! -f /models/${GGUF_FILENAME} ]; then \
    echo "[model-loader] Copying ${GGUF_FILENAME} into volume..."; \
    cp /model/${GGUF_FILENAME} /models/${GGUF_FILENAME}; \
    echo "[model-loader] Done."; \
  else \
    echo "[model-loader] Model already present, skipping."; \
  fi'
