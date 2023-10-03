# .NET Build
FROM mcr.microsoft.com/dotnet/sdk:6.0-alpine AS build
WORKDIR /src/app

RUN apk add --no-cache bash
COPY osu   /src/app/osu
COPY tools /src/app/tools
RUN \
  cd osu && mv .git ._git && cd .. ; \
  cd tools && mv .git ._git && cd .. ;
COPY .git/modules/osu.master /src/app/osu/.git
COPY .git/modules/osu.tools  /src/app/tools/.git
COPY patche[s] .patches
COPY docker/delta-patcher[s] .
RUN \
  ( \
    [ ! -f delta-patchers ] && echo 'Skipping Delta Patcher' >&2 \
  ) || ./delta-patchers
RUN \
  # Update dotnet project package references if needed.
  grep -qvF '"..\osu' tools/osu.Tools.sln || ( \
    cd tools && \
    ./UseLocalOsu.sh >/dev/null 2>/dev/null && \
    cd .. \
  ) ; \
  # Confirm .NET version
  dotnet --version && \
  # Publish Project
  dotnet publish --nologo \
    -c Release \
    -o /src/bin tools/PerformanceCalculator/PerformanceCalculator.csproj

# .NET Runtime
FROM mcr.microsoft.com/dotnet/runtime:6.0-jammy AS runner
# ARG PYTHON_VERSION
ENV TZ UTC
ENV DEBIAN_FRONTEND noninteractive

# RUN adduser -DH osu
RUN \
  useradd -M osu
#RUN \
#  apt update && \
#  apt install -y software-properties-common && \
#  add-apt-repository -y universe && \
#  add-apt-repository -y ppa:deadsnakes/ppa
RUN \
  apt update && \
  apt install -y python3 python3-pip python3-distutils python3-venv
  # apt install -y python"${PYTHON_VERSION}" python3-pip python3-distutils
#RUN \
#  apt install -y curl && \
#  #
#  update-alternatives --install $(which python3) python3 $(which python"${PYTHON_VERSION}") 1 && \
#  ln -s $(which python3) $(dirname $(which python3))/python && \
#  # python -V | grep -qE "\b""${PYTHON_VERSION}" && \
#  # curl -L "https://bootstrap.pypa.io/pip/get-pip.py" -o $HOME/get-pip.py && \
#  # python $HOME/get-pip.py
#  python -V
WORKDIR /app
RUN \
  chown -R 1000 .
USER osu

COPY --chown=1000 requirements.txt .
RUN \
  python3 -m venv . && \
  bin/python3 -m pip install --no-cache-dir -r requirements.txt

EXPOSE 5000
VOLUME /app/tmp
# ENV PYTHON_VERSION ${PYTHON_VERSION}
COPY --chown=1000 *.py .
COPY --chown=1000 docker/entrypoint.sh .

COPY --chown=1000 --from=build /src/bin osu
RUN \
  ln -s /app/tmp/cache /app/osu/cache

ENTRYPOINT ["./entrypoint.sh"]
