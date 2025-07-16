# DOCKER_BUILDKIT=1 docker build -t ocr-rt -f delivery/resources/Dockerfile.ocr_extensions delivery/resources/

ARG PYTHON_VERSION=3.12.7
FROM python:${PYTHON_VERSION}-slim

ENV IQ_PIP_EXTENSION_DIR=/extensions/pip_packages
ENV IQ_LIB_EXTENSION_DIR=/extensions/lib
ENV LD_LIBRARY_PATH="${IQ_LIB_EXTENSION_DIR}"

USER root

RUN apt-get update && apt-get install -y rsync && \
	apt-get install -y libgl1-mesa-glx libglib2.0-0 && \
	rm -rf /var/lib/apt/lists/*

RUN mkdir -p ${IQ_PIP_EXTENSION_DIR} ${IQ_LIB_EXTENSION_DIR}

# install pips for OCR directly into the extension folder
RUN pip install --target ${IQ_PIP_EXTENSION_DIR} \
	-Iv rapidocr-onnxruntime==1.4.4 pypdf==5.6.0 docx2txt==0.8 fsspec==2024.10.0 python-pptx==1.0.2

# copy necessary libraries to the extension folder
RUN dpkg -L libglib2.0-0 | grep '\.so' | xargs -I{} cp {} ${IQ_LIB_EXTENSION_DIR}
RUN dpkg -L libgl1-mesa-glx | grep '\.so' | xargs -I{} cp {} ${IQ_LIB_EXTENSION_DIR}

# remove dependency libs again, to make sure, they will be discovered from IQ_LIB_EXTENSION_DIR
RUN apt-get remove -y libgl1-mesa-glx libglib2.0-0 && \
	rm -rf /var/lib/apt/lists/*

# # for testing within the container
# RUN echo ${IQ_PIP_EXTENSION_DIR} > /usr/local/lib/python3.12/site-packages/extension_paths.pth
#
# # python
# # > from rapidocr_onnxruntime import RapidOCR
#
# CMD ["tail", "-f", "/dev/null"]
#
# USER nobody

COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT ["bash", "/entrypoint.sh"]

