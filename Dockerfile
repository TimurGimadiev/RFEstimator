FROM ubuntu:focal
ENV DEBIAN_FRONTEND noninteractive
RUN apt update && apt install wget git openbabel build-essential libatlas-base-dev \
 gfortran cmake python3 python3-pip python3-gdbm -y
RUN pip3 install -U pyscf[geomopt] cgrtools \
redis rq bigjson pyberny
RUN mkdir /data
RUN cd /opt && git clone https://github.com/grimme-lab/xtb.git
RUN cd /opt/xtb && cmake -B build -DCMAKE_BUILD_TYPE=Release &&\
 make -C build && make -C build test && make -C build install
RUN wget https://github.com/grimme-lab/crest/releases/download/v2.11/crest.tgz -P /opt/ && cd /opt/ \
&& tar -xvzf crest.tgz && rm /opt/crest.tgz
RUN apt purge build-essential gfortran git wget cmake -y
COPY README.md boot.sh setup.py /opt/
COPY Estimator /opt/Estimator
ENV PATH="/opt/orca:${PATH}"
RUN cd /opt && chmod +x boot.sh && chmod +x crest &&\
    pip3 --no-cache-dir install -U -e .
WORKDIR /data
ENV OMP_NUM_THREADS=1
COPY priroda /opt/priroda
ENTRYPOINT ["/opt/boot.sh"]

