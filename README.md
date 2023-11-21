# miso_nanopore_runscanner: A MISO LIMS Nanopore Run Scanner with pod5 and flowcell re-use support

This is a Python [FastAPI][] server to scan a directory for [Oxford Nanopore Technologies][] (ONT) sequencing 
runs producing [pod5][] output, extract information about those runs and provide that info to [MISO][] on request.
This tool tries to provide requests in the same way as the [official MISO Run Scanner](https://github.com/miso-lims/runscanner).

## Installation

### Poetry

This project uses [Poetry](https://python-poetry.org/) for dependency management.

To run with Poetry:

```bash
git clone https://github.com/CFIA-NCFAD/miso_nanopore_runscanner.git
cd miso_nanopore_runscanner
poetry install
# set environment variables
export HOST="127.0.0.1"
export PORT=8000
export DATABASE_URL="sqlite:///miso-nanopore-runscanner.db"
export BASEDIR="/path/to/ont-sequencing/data"
# run the server
poetry run start
```

### Docker

Run the server in a Docker container:

```bash
git clone https://github.com/CFIA-NCFAD/miso_nanopore_runscanner.git
cd miso_nanopore_runscanner
docker build -t miso-nanopore-runscanner .

cat << EOF > env.txt
HOST="0.0.0.0"
PORT=8000
DATABASE_URL="sqlite:////opt/miso/db/miso-nanopore-runscanner.db"
BASEDIR="/path/to/ont-sequencing/data"
EOF

mkdir db

docker run -d \
  -p 8000:8000 \
  --env-file env.txt \
  -v $(pwd)/db:/opt/miso/db \
  -v /path/to/ont-sequencing/data:/path/to/ont-sequencing/data \
  --name miso-nanopore-runscanner \
  miso-nanopore-runscanner
```

## Why?

The official Run Scanner depends on ONT [fast5][] output and does not yet support [pod5][].
It also does not support flowcell re-use, which can cause issues with properly linking runs to flowcells in MISO 
(see MISO issue [#2679](https://github.com/miso-lims/miso-lims/issues/2679)). 
So it's easier to just build out a new Nanopore only RunScanner that supports pod5 and flowcell re-use, 
especially since MISO can support scanning from multiple instances of RunScanner.

[FastAPI]: https://fastapi.tiangolo.com/
[MISO]: https://github.com/miso-lims/miso-lims
[Oxford Nanopore Technologies]: https://nanoporetech.com/
[pod5]: https://github.com/nanoporetech/pod5-file-format
[fast5]: https://github.com/nanoporetech/ont_fast5_api
